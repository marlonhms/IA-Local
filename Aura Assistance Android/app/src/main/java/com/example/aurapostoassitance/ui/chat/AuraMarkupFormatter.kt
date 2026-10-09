package com.example.aurapostoassitance.ui.chat

object AuraMarkupFormatter {

    private val colorHexMap = mapOf(
        "verde" to "#10B981",
        "vermelho" to "#EF4444",
        "amarelo" to "#F59E0B",
        "ciano" to "#06B6D4",
        "roxo" to "#8B5CF6"
    )

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
            "\\[(verde|vermelho|amarelo|ciano|roxo)\\]([\\s\\S]*?)(?:\\[\\s*/\\s*\\1\\s*\\]|\\s*(?:\\[\\s*)?[/\\\\]\\s*\\1\\b(?:\\])?)",
            RegexOption.IGNORE_CASE
        )
        result = result.replace(tolerantRegex) { match ->
            val color = match.groupValues[1].lowercase()
            val text = match.groupValues[2]
            val hex = colorHexMap[color] ?: "#06B6D4"
            "<font color=\"$hex\"><b>$text</b></font>"
        }

        // 2. Garante que tags abertas nao fechadas sejam fechadas antes da substituicao, aplicando a cor
        val unclosedRegex = Regex(
            "\\[(verde|vermelho|amarelo|ciano|roxo)\\]([^\\r\\n\\[<]+?)(?=(?:\\[/?(?:verde|vermelho|amarelo|ciano|roxo)\\]|\\r?\\n|$))",
            RegexOption.IGNORE_CASE
        )
        result = result.replace(unclosedRegex) { match ->
            val color = match.groupValues[1].lowercase()
            val text = match.groupValues[2]
            val trimmed = text.trim()
            if (trimmed.isNotEmpty()) {
                val hex = colorHexMap[color] ?: "#06B6D4"
                "<font color=\"$hex\"><b>$trimmed</b></font>"
            } else {
                text
            }
        }

        // 3. Limpa tags orfas remanescentes com colchetes: [cor], [/cor], etc.
        result = result.replace(Regex("\\[/?(verde|vermelho|amarelo|ciano|roxo)\\]", RegexOption.IGNORE_CASE), "")

        // 4. Limpa tags orfas remanescentes com barra ou soltas sem colchetes: /vermelho, /ciano, \vermelho, etc.
        result = result.replace(Regex("(?:^|\\s)[/\\\\](verde|vermelho|amarelo|ciano|roxo)\\b(?:\\s|$)?", RegexOption.IGNORE_CASE), " ")

        // 5. Normaliza espacamento residual
        result = result.replace(Regex("[^\\S\\r\\n]{2,}"), " ")
        result = result.replace(Regex("\\s+([,.:;!?])"), "$1")

        return result.trim()
    }
}
