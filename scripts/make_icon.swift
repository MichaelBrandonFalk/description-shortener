import AppKit
let output = CommandLine.arguments[1]
let size = 1024
let image = NSImage(size: NSSize(width: size, height: size))
image.lockFocus()
NSColor(calibratedRed: 0.10, green: 0.40, blue: 0.37, alpha: 1).setFill()
NSBezierPath(roundedRect: NSRect(x: 25, y: 25, width: 974, height: 974), xRadius: 210, yRadius: 210).fill()
NSColor.white.setFill()
NSBezierPath(roundedRect: NSRect(x: 220, y: 225, width: 584, height: 620), xRadius: 45, yRadius: 45).fill()
NSColor(calibratedRed: 0.10, green: 0.40, blue: 0.37, alpha: 0.32).setFill()
for (y,w) in [(700,400),(605,400),(510,290)] { NSBezierPath(roundedRect: NSRect(x: 310,y:y,width:w,height:38),xRadius:19,yRadius:19).fill() }
let attributes: [NSAttributedString.Key:Any] = [.font:NSFont.monospacedDigitSystemFont(ofSize:115,weight:.bold),.foregroundColor:NSColor(calibratedRed:0.10,green:0.40,blue:0.37,alpha:1)]
("110" as NSString).draw(at:NSPoint(x:310,y:310),withAttributes:attributes)
image.unlockFocus()
let bitmap=NSBitmapImageRep(data:image.tiffRepresentation!)!
try bitmap.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:output))
