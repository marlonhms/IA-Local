package com.example.aurapostoassitance.widget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews
import com.example.aurapostoassitance.MainActivity
import com.example.aurapostoassitance.R
import com.example.aurapostoassitance.ui.domain.AuraDomainAdapter
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

class AuraPulseWidgetProvider : AppWidgetProvider() {

    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        for (widgetId in appWidgetIds) {
            updateAppWidget(context, appWidgetManager, widgetId)
        }
    }

    companion object {
        private val json = Json { ignoreUnknownKeys = true; isLenient = true }

        fun updateAppWidget(context: Context, appWidgetManager: AppWidgetManager, appWidgetId: Int) {
            val views = RemoteViews(context.packageName, R.layout.widget_aura_pulse)
            val pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE

            val briefingIntent = Intent(context, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                putExtra("aura_shortcut_action", "play_briefing")
            }
            val briefingPending = PendingIntent.getActivity(context, 201, briefingIntent, pendingFlags)
            views.setOnClickPendingIntent(R.id.btn_widget_briefing, briefingPending)

            val openIntent = Intent(context, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            }
            val openPending = PendingIntent.getActivity(context, 202, openIntent, pendingFlags)
            views.setOnClickPendingIntent(R.id.btn_widget_open, openPending)

            // Lê o pack_id ativo e o último snapshot real do cofre offline
            val configPrefs = context.getSharedPreferences("aura_config", Context.MODE_PRIVATE)
            val activePack = AuraDomainAdapter.normalizePackId(
                configPrefs.getString("active_pack_id", AuraDomainAdapter.PACK_FUEL)
            )
            val profile = AuraDomainAdapter.profileFor(activePack)

            val vaultPrefs = context.getSharedPreferences("aura_offline_vault", Context.MODE_PRIVATE)
            val rawBriefing = vaultPrefs.getString("briefing_${profile.legacySegmentKey}", null)
            val scriptSummary = rawBriefing?.let { raw ->
                runCatching {
                    json.parseToJsonElement(raw).jsonObject["oralVoiceScript"]?.jsonPrimitive?.contentOrNull
                }.getOrNull()
            }?.takeIf { it.isNotBlank() }

            views.setTextViewText(R.id.tv_widget_title, "AURA • ${profile.shortLabel.uppercase()}")
            views.setTextViewText(
                R.id.tv_widget_npu_tag,
                if (scriptSummary != null) "VAULT SINCRONIZADO" else "CARBON READY"
            )
            views.setTextViewText(
                R.id.tv_widget_body,
                scriptSummary ?: "${profile.subtitle} — Toque para ouvir o resumo executivo ou abrir o cockpit."
            )

            appWidgetManager.updateAppWidget(appWidgetId, views)
        }

        fun updateAllWidgets(context: Context) {
            val appWidgetManager = AppWidgetManager.getInstance(context)
            val thisWidget = ComponentName(context, AuraPulseWidgetProvider::class.java)
            val allWidgetIds = appWidgetManager.getAppWidgetIds(thisWidget)
            for (widgetId in allWidgetIds) {
                updateAppWidget(context, appWidgetManager, widgetId)
            }
        }
    }
}
