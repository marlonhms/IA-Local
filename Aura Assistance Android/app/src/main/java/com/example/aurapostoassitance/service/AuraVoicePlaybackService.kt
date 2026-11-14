package com.example.aurapostoassitance.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.MediaMetadata
import android.media.session.MediaSession
import android.media.session.PlaybackState
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import com.example.aurapostoassitance.MainActivity
import com.example.aurapostoassitance.R
import com.example.aurapostoassitance.data.audio.AuraVoiceManager
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class AuraVoicePlaybackService : Service() {

    @Inject
    lateinit var voiceManager: AuraVoiceManager

    private var mediaSession: MediaSession? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var isPlaying = false

    companion object {
        const val CHANNEL_ID = "aura_voice_playback_channel"
        const val NOTIFICATION_ID = 301

        const val ACTION_START = "com.example.aurapostoassitance.ACTION_START_PLAYBACK"
        const val ACTION_PAUSE = "com.example.aurapostoassitance.ACTION_PAUSE_PLAYBACK"
        const val ACTION_STOP = "com.example.aurapostoassitance.ACTION_STOP_PLAYBACK"

        const val EXTRA_TITLE = "extra_voice_title"
        const val EXTRA_SUBTITLE = "extra_voice_subtitle"

        fun startPlayback(context: Context, title: String, subtitle: String = "Modo Sócio • Hexagon NPU") {
            val intent = Intent(context, AuraVoicePlaybackService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_TITLE, title)
                putExtra(EXTRA_SUBTITLE, subtitle)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stopPlayback(context: Context) {
            val intent = Intent(context, AuraVoicePlaybackService::class.java).apply {
                action = ACTION_STOP
            }
            context.startService(intent)
        }
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        setupMediaSession()
        setupWakeLock()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                val title = intent.getStringExtra(EXTRA_TITLE) ?: "Briefing Executivo Matinal"
                val subtitle = intent.getStringExtra(EXTRA_SUBTITLE) ?: "Modo Sócio • Hexagon NPU"
                startForegroundWithMedia(title, subtitle)
            }
            ACTION_PAUSE -> {
                voiceManager.stopSpeaking()
                updatePlaybackState(PlaybackState.STATE_PAUSED)
            }
            ACTION_STOP -> {
                cleanupAndStop()
            }
        }
        return START_NOT_STICKY
    }

    private fun setupMediaSession() {
        mediaSession = MediaSession(this, "AuraMediaSession").apply {
            setCallback(object : MediaSession.Callback() {
                override fun onPlay() {
                    // Retomada ou controle via Bluetooth / volante
                    updatePlaybackState(PlaybackState.STATE_PLAYING)
                }

                override fun onPause() {
                    voiceManager.stopSpeaking()
                    updatePlaybackState(PlaybackState.STATE_PAUSED)
                }

                override fun onStop() {
                    cleanupAndStop()
                }
            })
            setFlags(MediaSession.FLAG_HANDLES_MEDIA_BUTTONS or MediaSession.FLAG_HANDLES_TRANSPORT_CONTROLS)
            isActive = true
        }
    }

    private fun setupWakeLock() {
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "AuraAssistance:VoicePlaybackWakeLock")
    }

    private fun startForegroundWithMedia(title: String, subtitle: String) {
        isPlaying = true
        acquireWakeLock()
        updatePlaybackState(PlaybackState.STATE_PLAYING)

        mediaSession?.setMetadata(
            MediaMetadata.Builder()
                .putString(MediaMetadata.METADATA_KEY_TITLE, title)
                .putString(MediaMetadata.METADATA_KEY_ARTIST, "AURA Super-Inteligência")
                .putString(MediaMetadata.METADATA_KEY_ALBUM, subtitle)
                .build()
        )

        val notification = buildMediaNotification(title, subtitle, isPlaying = true)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun buildMediaNotification(title: String, subtitle: String, isPlaying: Boolean): Notification {
        val pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE

        // Intent para abrir o App no clique da notificação
        val contentIntent = Intent(this, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        }
        val contentPending = PendingIntent.getActivity(this, 301, contentIntent, pendingFlags)

        // Botão Play/Pause na tela de bloqueio
        val toggleActionIntent = Intent(this, AuraVoicePlaybackService::class.java).apply {
            action = if (isPlaying) ACTION_PAUSE else ACTION_START
            putExtra(EXTRA_TITLE, title)
            putExtra(EXTRA_SUBTITLE, subtitle)
        }
        val togglePending = PendingIntent.getService(this, 302, toggleActionIntent, pendingFlags)

        // Botão Stop
        val stopActionIntent = Intent(this, AuraVoicePlaybackService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPending = PendingIntent.getService(this, 303, stopActionIntent, pendingFlags)

        val sessionToken = mediaSession?.sessionToken

        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }

        builder
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(subtitle)
            .setContentIntent(contentPending)
            .setVisibility(Notification.VISIBILITY_PUBLIC)
            .setOngoing(isPlaying)
            .addAction(
                Notification.Action.Builder(
                    null,
                    if (isPlaying) "Pausar" else "Ouvir",
                    togglePending
                ).build()
            )
            .addAction(
                Notification.Action.Builder(
                    null,
                    "Parar",
                    stopPending
                ).build()
            )

        if (sessionToken != null) {
            builder.style = Notification.MediaStyle()
                .setMediaSession(sessionToken)
                .setShowActionsInCompactView(0, 1)
        }

        return builder.build()
    }

    private fun updatePlaybackState(state: Int) {
        val actions = PlaybackState.ACTION_PLAY or
            PlaybackState.ACTION_PAUSE or
            PlaybackState.ACTION_STOP or
            PlaybackState.ACTION_PLAY_PAUSE

        val stateBuilder = PlaybackState.Builder()
            .setActions(actions)
            .setState(state, PlaybackState.PLAYBACK_POSITION_UNKNOWN, 1.0f)

        mediaSession?.setPlaybackState(stateBuilder.build())
    }

    private fun acquireWakeLock() {
        wakeLock?.let {
            if (!it.isHeld) {
                // Timeout preventivo de 5 minutos para segurança de bateria
                it.acquire(5 * 60 * 1000L)
            }
        }
    }

    private fun releaseWakeLock() {
        wakeLock?.let {
            if (it.isHeld) {
                it.release()
            }
        }
    }

    private fun cleanupAndStop() {
        isPlaying = false
        voiceManager.stopSpeaking()
        updatePlaybackState(PlaybackState.STATE_STOPPED)
        releaseWakeLock()
        mediaSession?.isActive = false

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        stopSelf()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "AURA • Voz Executiva & Modo Carro",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Controles de reprodução de áudio da AURA na tela de bloqueio e modo carro"
                setShowBadge(false)
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        cleanupAndStop()
        mediaSession?.release()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
