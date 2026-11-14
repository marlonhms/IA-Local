package com.example.aurapostoassitance.service

import android.app.PendingIntent
import android.content.Intent
import android.os.Build
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import com.example.aurapostoassitance.MainActivity
import com.example.aurapostoassitance.data.audio.AuraVoiceManager
import com.example.aurapostoassitance.data.local.AuraOfflineVault
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class AuraQuickTileService : TileService() {

    @Inject
    lateinit var voiceManager: AuraVoiceManager

    @Inject
    lateinit var offlineVault: AuraOfflineVault

    override fun onStartListening() {
        super.onStartListening()
        updateTileState()
    }

    override fun onClick() {
        super.onClick()
        val tile = qsTile ?: return

        if (voiceManager.isSpeaking.value) {
            voiceManager.stopSpeaking()
            tile.state = Tile.STATE_INACTIVE
            tile.subtitle = "Pausado"
            tile.updateTile()
        } else {
            // Reproduz o briefing matinal executivo de 45s (Modo Sócio)
            val briefing = offlineVault.getBriefing("postos_redes")
            voiceManager.speak("tile_briefing", briefing.oralVoiceScript)

            tile.state = Tile.STATE_ACTIVE
            tile.subtitle = "Modo Sócio Ativo"
            tile.updateTile()

            // Abre o aplicativo colapsando a barra de notificações
            val launchIntent = Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
                putExtra("aura_shortcut_action", "play_briefing")
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
                val pending = PendingIntent.getActivity(
                    this,
                    101,
                    launchIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                startActivityAndCollapse(pending)
            } else {
                @Suppress("DEPRECATION")
                startActivityAndCollapse(launchIntent)
            }
        }
    }

    private fun updateTileState() {
        val tile = qsTile ?: return
        val isSpeaking = voiceManager.isSpeaking.value

        tile.label = "AURA Sócio"
        tile.subtitle = if (isSpeaking) "Voz Ativa (45s)" else "Briefing Matinal"
        tile.state = if (isSpeaking) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
        tile.updateTile()
    }
}
