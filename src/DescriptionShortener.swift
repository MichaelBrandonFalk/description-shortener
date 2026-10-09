import SwiftUI
import AppKit
import UniformTypeIdentifiers
import PDFKit

let appVersion = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0"
let ink = Color(red: 0.12, green: 0.22, blue: 0.24)
let teal = Color(red: 0.10, green: 0.40, blue: 0.37)
let paper = Color(red: 0.965, green: 0.961, blue: 0.941)

@MainActor final class Shortener: ObservableObject {
    @Published var mode = 0
    @Published var input = ""
    @Published var output = ""
    @Published var source: URL?
    @Published var busy = false
    @Published var status = "Everything stays on this Mac."
    @Published var issue = ""
    @Published var progress = 0.0
    @Published var saved: URL?
    @Published var review = ""
    @Published var showReview = false
    private var task: Process?
    private var buffer = Data()
    private var temporary: URL?
    private var chosenOutput: URL?
    private var convertedOutput: URL?
    private var conversionExtension: String?
    private var runID = UUID()
    private var receivedResult = false

    var ready: Bool { !busy && (mode == 0 ? !input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty : source != nil) }
    var conversionNote: String {
        guard let ext = source?.pathExtension.lowercased() else { return "" }
        if ext == "pdf" { return "PDF text is exported as TXT. Scanned PDFs need OCR before import." }
        if ["rtf", "doc", "odt"].contains(ext) { return "This format uses macOS document conversion. Complex layout may change." }
        return "An edited copy keeps the original format. Your source file stays untouched."
    }
    func selectFile() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = ["xlsx", "csv", "docx", "txt", "rtf", "doc", "odt", "pdf"].compactMap { UTType(filenameExtension: $0) }
        panel.canChooseDirectories = false
        if panel.runModal() == .OK, let url = panel.url { accept(url) }
    }
    func accept(_ url: URL) {
        guard !busy else { return }
        guard ["xlsx", "csv", "docx", "txt", "rtf", "doc", "odt", "pdf"].contains(url.pathExtension.lowercased()) else {
            issue = "Choose an XLSX, CSV, DOCX, TXT, RTF, DOC, ODT or PDF file."; return
        }
        source = url; mode = 1; saved = nil; issue = ""; review = ""
        status = "Ready to inspect \(url.lastPathComponent)."
    }
    func cleanup() {
        if let dir = temporary { try? FileManager.default.removeItem(at: dir) }
        temporary = nil
    }
    func cancel() {
        runID = UUID()
        task?.terminate(); task = nil
        busy = false; status = "Canceled. No result was exported."; progress = 0
        cleanup()
    }
    func run() {
        guard ready else { return }
        var destination: URL?
        if mode == 1, let source {
            let panel = NSSavePanel()
            let ext = source.pathExtension.lowercased() == "pdf" ? "txt" : source.pathExtension.lowercased()
            panel.allowedContentTypes = [UTType(filenameExtension: ext) ?? .data]
            panel.nameFieldStringValue = source.deletingPathExtension().lastPathComponent + "_shortened." + ext
            guard panel.runModal() == .OK, let url = panel.url else { return }
            if url.standardizedFileURL == source.standardizedFileURL || FileManager.default.fileExists(atPath: url.path) {
                issue = "Choose a new filename. Existing files and originals are never overwritten."; return
            }
            destination = url
        }
        output = ""; issue = ""; saved = nil; review = ""; busy = true; progress = 0
        status = "Inspecting input and loading the local model…"
        chosenOutput = destination; convertedOutput = nil; conversionExtension = nil
        receivedResult = false
        let id = UUID(); runID = id
        do {
            let resources = Bundle.main.resourceURL!
            let executable = resources.appendingPathComponent("helper/shortener-helper")
            guard FileManager.default.isExecutableFile(atPath: executable.path) else {
                throw NSError(domain: "App", code: 1, userInfo: [NSLocalizedDescriptionKey: "The bundled processor is missing. Reinstall the complete app."])
            }
            var request: [String: Any] = ["mode": "text", "text": input]
            if mode == 1, let source, let destination {
                var processingSource = source
                var processingDestination = destination
                let ext = source.pathExtension.lowercased()
                if ["pdf", "rtf", "doc", "odt"].contains(ext) {
                    let dir = FileManager.default.temporaryDirectory.appendingPathComponent("description-shortener-" + UUID().uuidString)
                    try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
                    temporary = dir
                    if ext == "pdf" {
                        guard let document = PDFDocument(url: source), !document.isEncrypted,
                              let text = document.string, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                            throw NSError(domain: "PDF", code: 1, userInfo: [NSLocalizedDescriptionKey: "This PDF has no readable text or is encrypted. Use an unencrypted document with selectable text."])
                        }
                        processingSource = dir.appendingPathComponent("input.txt")
                        try text.write(to: processingSource, atomically: true, encoding: .utf8)
                    } else {
                        processingSource = dir.appendingPathComponent("input.docx")
                        try convert(source, to: processingSource, format: "docx")
                        processingDestination = dir.appendingPathComponent("output.docx")
                        convertedOutput = processingDestination
                        conversionExtension = ext
                    }
                }
                request = ["mode": "file", "source": processingSource.path, "destination": processingDestination.path]
            }
            let process = Process()
            let inputPipe = Pipe(); let outputPipe = Pipe()
            process.executableURL = executable
            process.arguments = [resources.path]
            process.standardInput = inputPipe; process.standardOutput = outputPipe
            process.standardError = FileHandle.nullDevice
            buffer = Data()
            outputPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
                let data = handle.availableData
                if data.isEmpty { handle.readabilityHandler = nil; return }
                Task { @MainActor [weak self] in self?.consume(data, id: id) }
            }
            process.terminationHandler = { [weak self] ended in
                Task { @MainActor [weak self] in
                    // Pipe delivery is asynchronous; allow queued final output to arrive.
                    try? await Task.sleep(for: .milliseconds(300))
                    guard let self, self.runID == id else { return }
                    if !self.receivedResult { self.fail("The local processor stopped unexpectedly. Please try again.") }
                    self.task = nil
                }
            }
            task = process
            try process.run()
            inputPipe.fileHandleForWriting.write(try JSONSerialization.data(withJSONObject: request))
            try inputPipe.fileHandleForWriting.close()
        } catch { fail(error.localizedDescription) }
    }
    func convert(_ source: URL, to destination: URL, format: String) throws {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/textutil")
        process.arguments = ["-convert", format, "-output", destination.path, source.path]
        process.standardOutput = FileHandle.nullDevice; process.standardError = FileHandle.nullDevice
        try process.run(); process.waitUntilExit()
        guard process.terminationStatus == 0 else {
            throw NSError(domain: "Conversion", code: 1, userInfo: [NSLocalizedDescriptionKey: "macOS could not convert this document. Save it as DOCX and try again."])
        }
    }
    private func consume(_ data: Data, id: UUID) {
        guard id == runID else { return }
        buffer.append(data)
        while let newline = buffer.firstIndex(of: 10) {
            let line = buffer[..<newline]; buffer.removeSubrange(...newline)
            guard let event = try? JSONSerialization.jsonObject(with: line) as? [String: Any] else { continue }
            if event["event"] as? String == "progress" {
                let current = event["current"] as? Int ?? 0, total = event["total"] as? Int ?? 1
                progress = Double(max(0, current - 1)) / Double(max(total, 1))
                status = "Checking \(current) of \(total): \(event["location"] as? String ?? "description")"
            } else if event["event"] as? String == "result" {
                receivedResult = true
                if event["ok"] as? Bool == true {
                    do {
                        if let convertedOutput, let chosenOutput, let conversionExtension {
                            guard !FileManager.default.fileExists(atPath: chosenOutput.path) else {
                                throw NSError(domain: "Output", code: 1, userInfo: [NSLocalizedDescriptionKey: "The chosen output file now exists. Select a new filename."])
                            }
                            let staged = temporary!.appendingPathComponent("final." + conversionExtension)
                            try convert(convertedOutput, to: staged, format: conversionExtension)
                            try FileManager.default.copyItem(at: staged, to: chosenOutput)
                        }
                        if let text = event["text"] as? String {
                            output = text
                            let counts = event["counts"] as? [Int] ?? []
                            status = counts.count == 1 ? "\(counts.first ?? 0) / 110 characters" : "\(counts.count) descriptions checked. Each is 110 characters or fewer."
                        } else {
                            saved = chosenOutput
                            let count = event["checked"] as? Int ?? 0, changed = event["changed"] as? Int ?? 0
                            status = count == 0 ? "No description fields found. An unchanged copy was saved." : "Saved. \(count) checked, \(changed) changed."
                            let edits = event["edits"] as? [[String: Any]] ?? []
                            review = edits.map { "\($0["location"] as? String ?? "")\nOriginal: \($0["original"] as? String ?? "")\nResult: \($0["text"] as? String ?? "")\n\($0["characters"] as? Int ?? 0) / 110 characters" }.joined(separator: "\n\n")
                        }
                        progress = 1; busy = false; cleanup()
                    } catch { fail(error.localizedDescription) }
                } else {
                    let issues = event["issues"] as? [[String: Any]] ?? []
                    review = issues.map { "\($0["location"] as? String ?? "")\n\($0["original"] as? String ?? "")\n\($0["reason"] as? String ?? "Needs review")" }.joined(separator: "\n\n")
                    fail(event["error"] as? String ?? "\(issues.count) description(s) need review. No output file was exported. Open Review details for locations, then revise the source and try again.")
                }
            }
        }
    }
    private func fail(_ message: String) { issue = message; busy = false; status = "Needs review"; cleanup() }
    func copy() { NSPasteboard.general.clearContents(); NSPasteboard.general.setString(output, forType: .string) }
}

struct ContentView: View {
    @StateObject private var model = Shortener()
    @State private var dragOver = false
    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack(alignment: .top) {
                ZStack {
                    RoundedRectangle(cornerRadius: 16).fill(teal).frame(width: 54, height: 54)
                    Image(systemName: "text.badge.checkmark").font(.system(size: 25, weight: .medium)).foregroundStyle(.white)
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text("Description Shortener").font(.system(size: 28, weight: .semibold, design: .rounded))
                    Text("Less text. Same meaning.").font(.system(size: 14)).foregroundStyle(.secondary)
                }
                Spacer()
                Text("V\(appVersion)").font(.system(size: 12, weight: .medium, design: .monospaced)).padding(8).background(.white.opacity(0.8), in: Capsule())
            }
            HStack(spacing: 12) {
                Label("110 characters maximum", systemImage: "textformat.123")
                Label("Fully local", systemImage: "lock.shield")
                Label("No em dashes", systemImage: "checkmark.circle")
            }.font(.system(size: 12)).foregroundStyle(teal)
            Picker("Input", selection: $model.mode) {
                Text("Paste text").tag(0)
                Text("Process a file").tag(1)
            }.pickerStyle(.segmented).frame(width: 300).disabled(model.busy)
            if model.mode == 0 {
                HStack(alignment: .top, spacing: 18) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("ORIGINAL").font(.system(size: 11, weight: .semibold)).tracking(1.4)
                        TextEditor(text: $model.input).font(.system(size: 16)).scrollContentBackground(.hidden)
                            .padding(12).background(.white, in: RoundedRectangle(cornerRadius: 12))
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(ink.opacity(0.12)))
                            .disabled(model.busy).accessibilityLabel("Original descriptions")
                        Text("Paste one description per line.").font(.system(size: 12)).foregroundStyle(.secondary)
                    }
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("SHORTENED").font(.system(size: 11, weight: .semibold)).tracking(1.4)
                            Spacer()
                            Button(action: model.copy) { Label("Copy", systemImage: "doc.on.doc") }.disabled(model.output.isEmpty)
                        }
                        ScrollView {
                            Text(model.output.isEmpty ? "Your shortened text will appear here." : model.output)
                                .font(.system(size: 16)).foregroundStyle(model.output.isEmpty ? .secondary : ink)
                                .textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading).padding(14)
                        }.frame(maxWidth: .infinity, maxHeight: .infinity)
                            .background(teal.opacity(0.055), in: RoundedRectangle(cornerRadius: 12))
                        Text("Only the shortened text is copied.").font(.system(size: 12)).foregroundStyle(.secondary)
                    }
                }.frame(minHeight: 220)
            } else {
                VStack(spacing: 15) {
                    Image(systemName: model.source == nil ? "square.and.arrow.down" : "doc.text").font(.system(size: 37, weight: .light)).foregroundStyle(teal)
                    Text(model.source?.lastPathComponent ?? "Drop your file here").font(.system(size: 21, weight: .medium))
                    Text("XLSX · CSV · DOCX · TXT · RTF · DOC · ODT · PDF").font(.system(size: 12)).foregroundStyle(.secondary)
                    Button(model.source == nil ? "Choose a file…" : "Choose another file…", action: model.selectFile).disabled(model.busy)
                    Text(model.conversionNote).font(.system(size: 12)).foregroundStyle(.secondary).multilineTextAlignment(.center)
                }.frame(maxWidth: .infinity, maxHeight: .infinity).frame(minHeight: 220).padding(16)
                    .background(dragOver ? teal.opacity(0.12) : Color.white.opacity(0.8), in: RoundedRectangle(cornerRadius: 16))
                    .overlay(RoundedRectangle(cornerRadius: 16).strokeBorder(teal.opacity(0.3), style: StrokeStyle(lineWidth: 1, dash: [6])))
                    .onDrop(of: [.fileURL], isTargeted: $dragOver) { providers in
                        guard !model.busy, let provider = providers.first else { return false }
                        _ = provider.loadObject(ofClass: URL.self) { url, _ in
                            if let url { Task { @MainActor in model.accept(url) } }
                        }
                        return true
                    }
            }
            VStack(alignment: .leading, spacing: 10) {
                if !model.issue.isEmpty {
                    Label(model.issue, systemImage: "exclamationmark.circle").font(.system(size: 13)).foregroundStyle(Color(red: 0.60, green: 0.23, blue: 0.10)).textSelection(.enabled)
                }
                if model.busy { ProgressView(value: model.progress).tint(teal) }
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(model.status).font(.system(size: 13, weight: .medium))
                        Text("Meaning is checked by a local model. Review changed wording before use.").font(.system(size: 11)).foregroundStyle(.secondary)
                    }
                    Spacer()
                    if !model.review.isEmpty { Button("Review details") { model.showReview = true } }
                    if let saved = model.saved { Button("Show file") { NSWorkspace.shared.activateFileViewerSelecting([saved]) } }
                    if model.busy { Button("Cancel", action: model.cancel) }
                    Button(model.mode == 0 ? "Shorten description" : "Shorten & save copy", action: model.run)
                        .buttonStyle(.borderedProminent).tint(teal).controlSize(.large).disabled(!model.ready).keyboardShortcut(.return, modifiers: .command)
                }
            }
            Divider()
            HStack(spacing: 6) {
                Text("Built with open source:")
                Link("llama.cpp", destination: URL(string: "https://github.com/ggml-org/llama.cpp")!)
                Text("·")
                Link("Qwen3", destination: URL(string: "https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507")!)
                Text("·")
                Link("Unsloth", destination: URL(string: "https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF")!)
                Text("·")
                Link("lxml", destination: URL(string: "https://lxml.de/")!)
                Text("·")
                Link("Python", destination: URL(string: "https://www.python.org/")!)
                Text("·")
                Link("PyInstaller", destination: URL(string: "https://pyinstaller.org/")!)
                Spacer()
                Button("Licenses") { if let url = Bundle.main.resourceURL?.appendingPathComponent("licenses") { NSWorkspace.shared.open(url) } }.buttonStyle(.link)
            }.font(.system(size: 10)).foregroundStyle(.secondary)
        }.padding(30).background(paper).foregroundStyle(ink).frame(minWidth: 880, minHeight: 650)
            .onOpenURL { model.accept($0) }
            .onReceive(NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)) { _ in model.cancel() }
            .sheet(isPresented: $model.showReview) {
                VStack(alignment: .leading, spacing: 16) {
                    HStack { Text("Review details").font(.title2); Spacer(); Button("Done") { model.showReview = false } }
                    ScrollView { Text(model.review).font(.system(size: 14)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }
                }.padding(25).frame(width: 700, height: 500)
            }
    }
}

@main struct DescriptionShortenerApp: App {
    var body: some Scene {
        WindowGroup("Description Shortener V\(appVersion)") { ContentView() }
            .defaultSize(width: 1020, height: 720)
            .commands { CommandGroup(replacing: .newItem) {} }
    }
}
