// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "CosmosSynaptic",
    platforms: [.macOS(.v13), .iOS(.v16)],
    products: [.library(name: "CosmosSynaptic", targets: ["CosmosSynaptic"])],
    targets: [.target(name: "CosmosSynaptic")]
)
