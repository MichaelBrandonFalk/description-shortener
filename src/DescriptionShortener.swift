import SwiftUI
import AppKit
import UniformTypeIdentifiers
import PDFKit

let appVersion = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.2"
let ink = Color(red: 0.12, green: 0.22, blue: 0.24)
let teal = Color(red: 0.10, green: 0.40, blue: 0.37)
let paper = Color(red: 0.965, green: 0.961, blue: 0.941)

@MainActor final class Shortener: ObservableObject {
    @Published var characterLimit = max(110, UserDefaults.standard.object(forKey: "characterLimit") as? Int ?? 110) {
        didSet {
            UserDefaults.standard.set(characterLimit, forKey: "characterLimit")
            output = ""; status = ""; issue = ""; review = ""; saved = nil
        }
    }
    @Published var mode = 0
    @Published var input = ""
    @Published var output = ""
    @Published var source: URL?
    @Published var busy = false
    @Published var status = ""
    @Published var issue = ""
    @Published var progress = 0.0
    @Published var saved: URL?
    @Published var review = ""
    @Published var showReview = false
    private var task: Process?
    private var requestPipe: FileHandle?
    private var workerID = UUID()
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
        task?.terminate(); task = nil; requestPipe = nil; workerID = UUID()
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
        status = "Shortening and checking your description…"
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
            try ensureWorker()
            request["character_limit"] = characterLimit
            request["request_id"] = id.uuidString
            try send(request)
        } catch { fail(error.localizedDescription) }
    }
    func warmUp() {
        do {
            try ensureWorker()
            try send(["mode": "warm", "request_id": "warm"])
        } catch { fail(error.localizedDescription) }
    }
    private func send(_ request: [String: Any]) throws {
        var data = try JSONSerialization.data(withJSONObject: request)
        data.append(10)
        try requestPipe?.write(contentsOf: data)
    }
    private func ensureWorker() throws {
        if let task, task.isRunning { return }
        let resources = Bundle.main.resourceURL!
        let executable = resources.appendingPathComponent("helper/shortener-helper")
        let process = Process()
        let inputPipe = Pipe(); let outputPipe = Pipe()
        process.executableURL = executable
        process.arguments = [resources.path, "--serve"]
        process.standardInput = inputPipe; process.standardOutput = outputPipe
        process.standardError = FileHandle.nullDevice
        buffer = Data()
        let id = UUID(); workerID = id
        outputPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if data.isEmpty { handle.readabilityHandler = nil; return }
            Task { @MainActor [weak self] in self?.consume(data, worker: id) }
        }
        process.terminationHandler = { [weak self] _ in
            Task { @MainActor [weak self] in
                try? await Task.sleep(for: .milliseconds(200))
                guard let self, self.workerID == id else { return }
                if self.busy { self.fail("The local processor stopped. Please try again.") }
                self.task = nil; self.requestPipe = nil
            }
        }
        try process.run()
        task = process
        requestPipe = inputPipe.fileHandleForWriting
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
    private func consume(_ data: Data, worker: UUID) {
        guard worker == workerID else { return }
        buffer.append(data)
        while let newline = buffer.firstIndex(of: 10) {
            let line = buffer[..<newline]; buffer.removeSubrange(...newline)
            guard let event = try? JSONSerialization.jsonObject(with: line) as? [String: Any] else { continue }
            if event["event"] as? String == "ready" {
                if event["ok"] as? Bool != true { fail(event["error"] as? String ?? "The local model could not load.") }
                continue
            }
            guard event["request_id"] as? String == runID.uuidString else { continue }
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
                            status = counts.count == 1 ? "\(counts.first ?? 0) / \(characterLimit) characters" : "\(counts.count) descriptions checked. Each is \(characterLimit) characters or fewer."
                        } else {
                            saved = chosenOutput
                            let count = event["checked"] as? Int ?? 0, changed = event["changed"] as? Int ?? 0
                            status = count == 0 ? "No description fields found. An unchanged copy was saved." : "Saved. \(count) checked, \(changed) changed."
                            let edits = event["edits"] as? [[String: Any]] ?? []
                            review = edits.map { "\($0["location"] as? String ?? "")\nOriginal: \($0["original"] as? String ?? "")\nResult: \($0["text"] as? String ?? "")\n\($0["characters"] as? Int ?? 0) / \(characterLimit) characters" }.joined(separator: "\n\n")
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
    @State private var showSettings = false
    @State private var limitDraft = "110"
    private var validLimit: Int? {
        guard let value = Int(limitDraft), value >= 110 else { return nil }; return value
    }
    private func inputButton(_ title: String, icon: String, mode: Int) -> some View {
        Button { model.mode = mode; model.issue = ""; model.status = "" } label: {
            Label(title, systemImage: icon)
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(model.mode == mode ? Color.white : ink)
                .padding(.horizontal, 18).padding(.vertical, 11)
                .background(model.mode == mode ? teal : Color.clear, in: RoundedRectangle(cornerRadius: 7))
        }.buttonStyle(.plain).disabled(model.busy)
            .accessibilityAddTraits(model.mode == mode ? .isSelected : [])
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack(alignment: .top) {
                ZStack {
                    RoundedRectangle(cornerRadius: 16).fill(teal).frame(width: 54, height: 54)
                    Image(systemName: "text.badge.checkmark").font(.system(size: 25, weight: .medium)).foregroundStyle(.white)
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text("Description Shortener").font(.system(size: 28, weight: .semibold, design: .rounded))

                }
                Spacer()
                Text("V\(appVersion)").font(.system(size: 12, weight: .medium, design: .monospaced)).padding(8).background(.white.opacity(0.8), in: Capsule())
            }
            HStack(spacing: 14) {
                HStack(spacing: 4) {
                    inputButton("Paste text", icon: "text.cursor", mode: 0)
                    inputButton("Process a file", icon: "doc", mode: 1)
                }.padding(4).background(Color.white, in: RoundedRectangle(cornerRadius: 10))
                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(ink.opacity(0.15)))
                Spacer()
                Text("\(model.characterLimit) characters maximum").font(.system(size: 12)).foregroundStyle(ink.opacity(0.75))
                Button { limitDraft = String(model.characterLimit); showSettings = true } label: {
                    Label("Settings", systemImage: "gearshape")
                }.disabled(model.busy)
            }
            if model.mode == 0 {
                HStack(alignment: .top, spacing: 18) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("ORIGINAL").font(.system(size: 11, weight: .semibold)).tracking(1.4)
                        TextEditor(text: $model.input).font(.system(size: 16)).scrollContentBackground(.hidden)
                            .padding(12).background(.white, in: RoundedRectangle(cornerRadius: 12))
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(ink.opacity(0.12)))
                            .disabled(model.busy).accessibilityLabel("Original descriptions")
                        Text("Paste one description per line.").font(.system(size: 12)).foregroundStyle(ink.opacity(0.65))
                    }
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("SHORTENED").font(.system(size: 11, weight: .semibold)).tracking(1.4)
                            Spacer()
                            Button(action: model.copy) { Label("Copy", systemImage: "doc.on.doc") }.disabled(model.output.isEmpty)
                        }
                        ScrollView {
                            Text(model.output.isEmpty ? "Shortened text" : model.output)
                                .font(.system(size: 16)).foregroundStyle(model.output.isEmpty ? ink.opacity(0.5) : ink)
                                .textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading).padding(14)
                        }.frame(maxWidth: .infinity, maxHeight: .infinity)
                            .background(teal.opacity(0.055), in: RoundedRectangle(cornerRadius: 12))

                    }
                }.frame(minHeight: 220)
            } else {
                VStack(spacing: 15) {
                    Image(systemName: model.source == nil ? "square.and.arrow.down" : "doc.text").font(.system(size: 37, weight: .light)).foregroundStyle(teal)
                    Text(model.source?.lastPathComponent ?? "Drop your file here").font(.system(size: 21, weight: .medium))
                    Text("XLSX · CSV · DOCX · TXT · RTF · DOC · ODT · PDF").font(.system(size: 12)).foregroundStyle(ink.opacity(0.65))
                    Button(model.source == nil ? "Choose a file…" : "Choose another file…", action: model.selectFile).disabled(model.busy)
                    Text(model.conversionNote).font(.system(size: 12)).foregroundStyle(ink.opacity(0.65)).multilineTextAlignment(.center)
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
                Link("Gemma 4", destination: URL(string: "https://huggingface.co/google/gemma-4-12B-it")!)
                Text("·")
                Link("Google GGUF", destination: URL(string: "https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf")!)
                Text("·")
                Link("lxml", destination: URL(string: "https://lxml.de/")!)
                Text("·")
                Link("Python", destination: URL(string: "https://www.python.org/")!)
                Text("·")
                Link("PyInstaller", destination: URL(string: "https://pyinstaller.org/")!)
                Spacer()
                Button("Licenses") { if let url = Bundle.main.resourceURL?.appendingPathComponent("licenses") { NSWorkspace.shared.open(url) } }.buttonStyle(.link)
            }.font(.system(size: 10)).foregroundStyle(ink.opacity(0.65))
        }.padding(30).background(paper).foregroundStyle(ink).frame(minWidth: 880, minHeight: 600)
            .preferredColorScheme(.light)
            .task { model.warmUp() }
            .onOpenURL { model.accept($0) }
            .onReceive(NotificationCenter.default.publisher(for: NSApplication.willTerminateNotification)) { _ in model.cancel() }
            .sheet(isPresented: $showSettings) {
                VStack(alignment: .leading, spacing: 16) {
                    Text("Settings").font(.title2)
                    Text("Maximum characters per description")
                    TextField("Character limit", text: $limitDraft).textFieldStyle(.roundedBorder)
                        .accessibilityLabel("Character limit")
                    Text("Minimum 110. Spaces, punctuation and all other characters count toward the total.")
                        .font(.system(size: 12)).foregroundStyle(ink.opacity(0.75))
                    if validLimit == nil { Text("Enter a whole number of at least 110.").foregroundStyle(.red) }
                    HStack {
                        Button("Reset to 110") { limitDraft = "110" }
                        Spacer()
                        Button("Cancel") { showSettings = false }
                        Button("Save") {
                            if let limit = validLimit { model.characterLimit = limit; showSettings = false }
                        }.buttonStyle(.borderedProminent).tint(teal).disabled(validLimit == nil)
                    }
                }.padding(25).frame(width: 440)
            }
            .sheet(isPresented: $model.showReview) {
                VStack(alignment: .leading, spacing: 16) {
                    HStack { Text("Review details").font(.title2); Spacer(); Button("Done") { model.showReview = false } }
                    ScrollView { Text(model.review).font(.system(size: 14)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading) }
                }.padding(25).frame(width: 700, height: 500)
            }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

@main struct DescriptionShortenerApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    var body: some Scene {
        WindowGroup("Description Shortener V\(appVersion)") { ContentView() }
            .defaultSize(width: 1020, height: 680)
            .commands { CommandGroup(replacing: .newItem) {} }
    }
}
