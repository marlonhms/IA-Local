package com.example.aurapostoassitance.ui.chat

object AuraMarkupFormatter {

    /**
     * Converts AURA custom BBCode-style tags into HTML styling compatible with Compose Markdown.
     * Example: [ciano]R$ 71,30[/ciano] -> <font color="#06B6D4"><b>R$ 71,30</b></font>
     */
    fun format(input: String): String {
        if (input.isBlank()) return input

        var result = input

        // Replace colored tags
        result = result.replace(Regex("\\[verde\\](.*?)\\[/verde\\]", RegexOption.IGNORE_CASE)) {
            "<font color=\"#10B981\"><b>${it.groupValues[1]}</b></font>"
        }
        result = result.replace(Regex("\\[vermelho\\](.*?)\\[/vermelho\\]", RegexOption.IGNORE_CASE)) {
            "<font color=\"#EF4444\"><b>${it.groupValues[1]}</b></font>"
        }
        result = result.replace(Regex("\\[amarelo\\](.*?)\\[/amarelo\\]", RegexOption.IGNORE_CASE)) {
            "<font color=\"#F59E0B\"><b>${it.groupValues[1]}</b></font>"
        }
        result = result.replace(Regex("\\[ciano\\](.*?)\\[/ciano\\]", RegexOption.IGNORE_CASE)) {
            "<font color=\"#06B6D4\"><b>${it.groupValues[1]}</b></font>"
        }
        result = result.replace(Regex("\\[roxo\\](.*?)\\[/roxo\\]", RegexOption.IGNORE_CASE)) {
            "<font color=\"#8B5CF6\"><b>${it.groupValues[1]}</b></font>"
        }

        // Clean up remaining dangling unclosed tags if any
        result = result.replace(Regex("\\[/?(verde|vermelho|amarelo|ciano|roxo)\\]", RegexOption.IGNORE_CASE), "")

        return result
    }
}
