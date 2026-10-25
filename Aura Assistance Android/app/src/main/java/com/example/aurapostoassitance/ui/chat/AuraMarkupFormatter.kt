package com.example.aurapostoassitance.ui.chat

object AuraMarkupFormatter {

    private val colorHexMap = mapOf(
        "verde" to "#10B981",
        "emerald" to "#10B981",
        "green" to "#10B981",
        "sucesso" to "#10B981",
        "vermelho" to "#EF4444",
        "rose" to "#EF4444",
        "red" to "#EF4444",
        "perigo" to "#EF4444",
        "amarelo" to "#F59E0B",
        "amber" to "#F59E0B",
        "yellow" to "#F59E0B",
        "alerta" to "#F59E0B",
        "ciano" to "#06B6D4",
        "cyan" to "#06B6D4",
        "destaque" to "#06B6D4",
        "roxo" to "#8B5CF6",
        "purple" to "#8B5CF6",
        "azul" to "#38BDF8",
        "blue" to "#38BDF8"
    )

    private const val COLOR_NAMES = "verde|emerald|green|sucesso|amarelo|amber|yellow|alerta|vermelho|rose|red|perigo|ciano|cyan|destaque|roxo|purple|azul|blue"
    private const val STYLE_NAMES = "sublinhado|italico|negrito|u|i|b"
    private const val ALL_TAG_NAMES = "(?:badge-)?(?:$COLOR_NAMES)|$STYLE_NAMES"

    /**
     * Converte tags personalizadas de estilo da AURA (ex: [ciano], [sublinhado], [italico]) para formatacao compativel com Compose Markdown.
     * Suporta fechamentos tolerantes (ex: [/cor], /cor) e auto-fecha tags abertas antes de aplicar estilo.
     */
    fun format(input: String): String {
        if (input.isBlank()) return input

        var result = input

        // 1. Tags de estilo tipografico (sublinhado, italico, negrito) com fechamento canonico ou tolerante
        result = result.replace(
            Regex("\\[(sublinhado|u)\\]((?:(?!\\[(?:$ALL_TAG_NAMES)\\])[\\s\\S])*?)(?:\\[\\s*/\\s*\\1\\s*\\]|\\s*(?:\\[\\s*)?[/\\\\]\\s*\\1\\b(?:\\])?)", RegexOption.IGNORE_CASE)
        ) { m -> "<u>${m.groupValues[2].trim()}</u>" }

        result = result.replace(
            Regex("\\[(italico|i)\\]((?:(?!\\[(?:$ALL_TAG_NAMES)\\])[\\s\\S])*?)(?:\\[\\s*/\\s*\\1\\s*\\]|\\s*(?:\\[\\s*)?[/\\\\]\\s*\\1\\b(?:\\])?)", RegexOption.IGNORE_CASE)
        ) { m -> "<i>${m.groupValues[2].trim()}</i>" }

        result = result.replace(
            Regex("\\[(negrito|b)\\]((?:(?!\\[(?:$ALL_TAG_NAMES)\\])[\\s\\S])*?)(?:\\[\\s*/\\s*\\1\\s*\\]|\\s*(?:\\[\\s*)?[/\\\\]\\s*\\1\\b(?:\\])?)", RegexOption.IGNORE_CASE)
        ) { m -> "<b>${m.groupValues[2].trim()}</b>" }

        // 2. Substitui tags coloridas com fechamento canonico ou tolerante
        val tolerantColorRegex = Regex(
            "\\[((?:badge-)?(?:$COLOR_NAMES))\\]((?:(?!\\[(?:$ALL_TAG_NAMES)\\])[\\s\\S])*?)(?:\\[\\s*/\\s*\\1\\s*\\]|\\s*(?:\\[\\s*)?[/\\\\]\\s*\\1\\b(?:\\])?)",
            RegexOption.IGNORE_CASE
        )
        result = result.replace(tolerantColorRegex) { match ->
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

        // 3. Garante que tags abertas nao fechadas no fim de linha ou bloco sejam estilizadas
        val unclosedColorRegex = Regex(
            "\\[((?:badge-)?(?:$COLOR_NAMES))\\](?!\\[|\\s)([^\r\n\\[<]+?)(?=(?:\\[/?(?:$ALL_TAG_NAMES)\\]|\r?\n|$))",
            RegexOption.IGNORE_CASE
        )
        result = result.replace(unclosedColorRegex) { match ->
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

        val unclosedStyleRegex = Regex(
            "\\[(sublinhado|italico|negrito|u|i|b)\\](?!\\[|\\s)([^\r\n\\[<]+?)(?=(?:\\[/?(?:$ALL_TAG_NAMES)\\]|\r?\n|$))",
            RegexOption.IGNORE_CASE
        )
        result = result.replace(unclosedStyleRegex) { match ->
            val tag = match.groupValues[1].lowercase()
            val text = match.groupValues[2].trim()
            when (tag) {
                "sublinhado", "u" -> "<u>$text</u>"
                "italico", "i" -> "<i>$text</i>"
                "negrito", "b" -> "<b>$text</b>"
                else -> text
            }
        }

        // 4. Limpa tags orfas remanescentes com colchetes: [cor], [/cor], etc.
        result = result.replace(Regex("\\s*\\[\\s*/\\s*(?:$ALL_TAG_NAMES)\\s*\\]\\s*", RegexOption.IGNORE_CASE), " ")
        result = result.replace(Regex("(?:^|\\s)\\[\\s*(?:$ALL_TAG_NAMES)\\s*\\](?=\\s|$|\\[)", RegexOption.IGNORE_CASE), " ")
        result = result.replace(Regex("\\[\\s*(?:$ALL_TAG_NAMES)\\s*\\]", RegexOption.IGNORE_CASE), " ")

        // 5. Limpa tags orfas remanescentes com barra solta
        result = result.replace(Regex("(?:^|\\s)[/\\\\](?:$ALL_TAG_NAMES)\\b(?:\\s|$)?", RegexOption.IGNORE_CASE), " ")

        // 6. Normaliza marcadores de lista para garantir renderizacao de topicos no Markdown
        result = result.replace(Regex("(?<=[^\r\n])\r?\n([*-]|●)\\s+")) {
            "\n\n* "
        }

        // 7. Normaliza espacamento residual
        result = result.replace(Regex("[^\\S\r\n]{2,}"), " ")
        result = result.replace(Regex("\\s+([,.:;!?])"), "$1")

        return result.trim()
    }
}
