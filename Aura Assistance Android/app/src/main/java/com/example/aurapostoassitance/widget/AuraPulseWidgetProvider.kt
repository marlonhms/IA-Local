package com.example.aurapostoassitance.widget

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.widget.RemoteViews
import com.example.aurapostoassitance.MainActivity
import com.example.aurapostoassitance.R

class AuraPulseWidgetProvider : AppWidgetProvider() {

    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        for (widgetId in appWidgetIds) {
            updateAppWidget(context, appWidgetManager, widgetId)
        }
    }

    companion object {
        fun updateAppWidget(context: Context, appWidgetManager: AppWidgetManager, appWidgetId: Int) {
            val views = RemoteViews(context.packageName, R.layout.widget_aura_pulse)

            val pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE

            // Intent para reproduzir o briefing matinal (Modo Sócio)
            val briefingIntent = Intent(context, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                putExtra("aura_shortcut_action", "play_briefing")
            }
            val briefingPending = PendingIntent.getActivity(context, 201, briefingIntent, pendingFlags)
            views.setOnClickPendingIntent(R.id.btn_widget_briefing, briefingPending)

            // Intent para abrir o Cockpit da AURA
            val openIntent = Intent(context, MainActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            }
            val openPending = PendingIntent.getActivity(context, 202, openIntent, pendingFlags)
            views.setOnClickPendingIntent(R.id.btn_widget_open, openPending)

            // Recupera texto do snapshot offline se disponível
            val prefs = context.getSharedPreferences("aura_offline_vault", Context.MODE_PRIVATE)
            val rawBriefing = prefs.getString("briefing_postos_redes", null)
            if (!rawBriefing.isNullOrBlank() && rawBriefing.contains("oralVoiceScript")) {
                views.setTextViewText(R.id.tv_widget_npu_tag, "HEXAGON NPU • OK")
            } else {
                views.setTextViewText(R.id.tv_widget_npu_tag, "SNAPDRAGON 7S NPU")
            }

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
