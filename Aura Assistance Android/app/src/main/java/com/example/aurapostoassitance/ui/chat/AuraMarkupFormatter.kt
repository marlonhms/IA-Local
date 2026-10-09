package com.example.aurapostoassitance.ui.chat

object AuraMarkupFormatter {

    private val colorHexMap = mapOf(
        "verde" to "#10B981",
        "emerald" to "#10B981",
        "green" to "#10B981",
        "vermelho" to "#EF4444",
        "rose" to "#EF4444",
        "red" to "#EF4444",
        "amarelo" to "#F59E0B",
        "amber" to "#F59E0B",
        "yellow" to "#F59E0B",
        "ciano" to "#06B6D4",
        "cyan" to "#06B6D4",
        "roxo" to "#8B5CF6",
        "purple" to "#8B5CF6"
    )

    private const val COLOR_NAMES = "verde|emerald|green|amarelo|amber|yellow|vermelho|rose|red|ciano|cyan|roxo|purple"
    private const val TAG_NAMES = "(?:badge-)?(?:$COLOR_NAMES)|u"

    /**
     * Converts AURA custom BBCode-style tags into HTML styling compatible with Compose Markdown.
     * Example: [ciano]R$ 71,30[/ciano] -> <font color="#06B6D4"><b>R$ 71,30</b></font>
     * Supports tolerant closures (e.g. /vermelho) and auto-closes unclosed tags before styling.
     */
    fun format(input: String): String {
        if (input.isBlank()) return input

        var result = input

        // 1. Substitui tags coloridas com fechamento canonico ou tolerante (ex: [/cor], [/ cor], /cor)
        val tolerantRegex = Regex(
            "\\[($TAG_NAMES)\\]((?:(?!\\[(?:$TAG_NAMES)\\])[\\s\\S])*?)(?:\\[\\s*/\\s*\\1\\s*\\]|\\s*(?:\\[\\s*)?[/\\\\]\\s*\\1\\b(?:\\])?)",
            RegexOption.IGNORE_CASE
        )
        result = result.replace(tolerantRegex) { match ->
            val rawTag = match.groupValues[1].lowercase()
            val colorKey = rawTag.removePrefix("badge-")
            val text = match.groupValues[2].trim()
            if (text.isNotEmpty()) {
                val hex = colorHexMap[colorKey] ?: "#06B6D4"
                "<font color=\"$hex\"><b>$text</b></font>"
            } else {
                ""
            }
        }

        // 2. Garante que tags abertas nao fechadas com termo colado sejam fechadas, aplicando a cor
        val unclosedRegex = Regex(
            "\\[($TAG_NAMES)\\](?!\\[|\\s)([^\r\n\\[<]+?)(?=(?:\\[/?(?:$TAG_NAMES)\\]|\r?\n|$))",
            RegexOption.IGNORE_CASE
        )
        result = result.replace(unclosedRegex) { match ->
            val rawTag = match.groupValues[1].lowercase()
            val colorKey = rawTag.removePrefix("badge-")
            val text = match.groupValues[2].trim()
            if (text.isNotEmpty()) {
                val hex = colorHexMap[colorKey] ?: "#06B6D4"
                "<font color=\"$hex\"><b>$text</b></font>"
            } else {
                ""
            }
        }

        // 3. Limpa tags orfas remanescentes com colchetes: [cor], [/cor], etc.
        result = result.replace(Regex("\\s*\\[\\s*/\\s*(?:$TAG_NAMES)\\s*\\]\\s*", RegexOption.IGNORE_CASE), " ")
        result = result.replace(Regex("(?:^|\\s)\\[\\s*(?:$TAG_NAMES)\\s*\\](?=\\s|$|\\[)", RegexOption.IGNORE_CASE), " ")
        result = result.replace(Regex("\\[\\s*(?:$TAG_NAMES)\\s*\\]", RegexOption.IGNORE_CASE), " ")

        // 4. Limpa tags orfas remanescentes com barra ou soltas sem colchetes: /vermelho, /ciano, \vermelho, etc.
        result = result.replace(Regex("(?:^|\\s)[/\\\\](?:$TAG_NAMES)\\b(?:\\s|$)?", RegexOption.IGNORE_CASE), " ")

        // 5. Normaliza espacamento residual
        result = result.replace(Regex("[^\\S\r\n]{2,}"), " ")
        result = result.replace(Regex("\\s+([,.:;!?])"), "$1")

        return result.trim()
    }
}
