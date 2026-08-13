package cosmos.sdk

import java.security.MessageDigest
import kotlin.math.PI
import kotlin.math.sin
import kotlin.math.tanh

class SynapticCore(context: String = "") {
    companion object { const val N = 12 }
    val values = vector(context)
    val weights = Array(N) { DoubleArray(N) }
    var step: Long = 0
        private set

    fun project(): DoubleArray = DoubleArray(N) { j -> tanh((0 until N).sumOf { i -> values[i] * weights[i][j] } / N) }

    fun advance(input: String): DoubleArray {
        val before = values.copyOf(); val stim = vector(input); val bias = project(); val phase = (step + 1) * 0.37
        val next = DoubleArray(N) { i ->
            val rec = sin(phase + i * PI / 6.0) * (before[(i + N - 1) % N] - before[(i + 1) % N]) * 0.18
            tanh(0.82 * before[i] + 0.33 * stim[i] + 0.25 * bias[i] + rec)
        }
        for (i in 0 until N) for (j in 0 until N) weights[i][j] = (0.995 * weights[i][j] + 0.04 * before[i] * next[j]).coerceIn(-1.0, 1.0)
        next.copyInto(values); step++; return next.copyOf()
    }

    private fun vector(text: String): DoubleArray {
        val d = MessageDigest.getInstance("SHA-256").digest("0:$text".toByteArray(Charsets.UTF_8))
        return DoubleArray(N) { i -> (((((d[2*i].toInt() and 255) shl 8) or (d[2*i+1].toInt() and 255)).toDouble() / 65535.0) * 2.0) - 1.0 }
    }
}
