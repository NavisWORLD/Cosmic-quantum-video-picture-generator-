import Foundation
import CryptoKit

public final class SynapticCore {
    public static let dimensions = 12
    public private(set) var values: [Double]
    public private(set) var weights = Array(repeating: Array(repeating: 0.0, count: 12), count: 12)
    public private(set) var step: UInt64 = 0

    public init(context: String = "") { values = Self.vector(context) }

    public func project() -> [Double] {
        (0..<12).map { j in tanh((0..<12).reduce(0.0) { $0 + values[$1] * weights[$1][j] } / 12.0) }
    }

    @discardableResult public func advance(_ input: String) -> [Double] {
        let before = values, stim = Self.vector(input), bias = project(), phase = Double(step + 1) * 0.37
        let next = (0..<12).map { i -> Double in
            let rec = sin(phase + Double(i) * .pi / 6.0) * (before[(i + 11) % 12] - before[(i + 1) % 12]) * 0.18
            return tanh(0.82 * before[i] + 0.33 * stim[i] + 0.25 * bias[i] + rec)
        }
        for i in 0..<12 { for j in 0..<12 { weights[i][j] = min(1.0, max(-1.0, 0.995 * weights[i][j] + 0.04 * before[i] * next[j])) } }
        values = next; step += 1; return next
    }

    static func vector(_ text: String) -> [Double] {
        let digest = Array(SHA256.hash(data: Data(("0:" + text).utf8)))
        return (0..<12).map { i in
            let raw = UInt16(digest[2*i]) << 8 | UInt16(digest[2*i+1])
            return (Double(raw) / 65535.0) * 2.0 - 1.0
        }
    }
}
