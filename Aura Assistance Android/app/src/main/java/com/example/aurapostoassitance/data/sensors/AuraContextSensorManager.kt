package com.example.aurapostoassitance.data.sensors

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.os.Build
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.sqrt

data class AuraPhysicalContext(
    val isCarOrBluetoothConnected: Boolean = false,
    val audioDeviceName: String? = null,
    val isMoving: Boolean = false,
    val isCarModeActive: Boolean = false,
    val recommendedModeLabel: String = "Cockpit Executivo Padrão"
)

/**
 * Gerenciador de Fusão de Sensores e Detecção Automática de Modo Carro / Hands-Free.
 * Otimizado para eficiência energética: o acelerômetro só é registrado enquanto houver
 * dispositivo de áudio Bluetooth/Headset conectado, evitando dreno contínuo de bateria.
 */
@Singleton
class AuraContextSensorManager @Inject constructor(
    @param:ApplicationContext private val context: Context
) : SensorEventListener {

    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as? SensorManager

    private val _contextState = MutableStateFlow(AuraPhysicalContext())
    val contextState: StateFlow<AuraPhysicalContext> = _contextState.asStateFlow()

    private var manualCarModeOverride: Boolean? = null
    private var lastMovementCheckTime: Long = 0

    @Volatile
    private var isMotionSensorRegistered: Boolean = false

    init {
        checkCurrentAudioDevices()
        registerAudioCallback()
    }

    fun toggleManualCarMode() {
        val current = _contextState.value.isCarModeActive
        val newManual = !current
        manualCarModeOverride = newManual
        updateState()
    }

    private fun registerAudioCallback() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && audioManager != null) {
            audioManager.registerAudioDeviceCallback(object : AudioDeviceCallback() {
                override fun onAudioDevicesAdded(addedDevices: Array<out AudioDeviceInfo>?) {
                    checkCurrentAudioDevices()
                }

                override fun onAudioDevicesRemoved(removedDevices: Array<out AudioDeviceInfo>?) {
                    checkCurrentAudioDevices()
                }
            }, null)
        }
    }

    private fun checkCurrentAudioDevices() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && audioManager != null) {
            val devices = audioManager.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
            var hasBt = false
            var devName: String? = null

            for (device in devices) {
                when (device.type) {
                    AudioDeviceInfo.TYPE_BLUETOOTH_A2DP,
                    AudioDeviceInfo.TYPE_BLUETOOTH_SCO,
                    AudioDeviceInfo.TYPE_BLE_HEADSET,
                    AudioDeviceInfo.TYPE_HEARING_AID -> {
                        hasBt = true
                        val prodName = device.productName?.toString()
                        devName = if (!prodName.isNullOrBlank()) prodName else "Bluetooth Áudio"
                        break
                    }
                    AudioDeviceInfo.TYPE_USB_HEADSET,
                    AudioDeviceInfo.TYPE_WIRED_HEADSET,
                    AudioDeviceInfo.TYPE_WIRED_HEADPHONES -> {
                        hasBt = true
                        devName = "Headset Conectado"
                    }
                }
            }

            // Só liga o acelerômetro quando houver Bluetooth/Headset ativo (zero dreno em idle)
            if (hasBt) {
                registerMotionSensor()
            } else {
                unregisterMotionSensor()
            }

            _contextState.value = _contextState.value.copy(
                isCarOrBluetoothConnected = hasBt,
                audioDeviceName = devName,
                isMoving = if (hasBt) _contextState.value.isMoving else false
            )
            updateState()
        }
    }

    @Synchronized
    private fun registerMotionSensor() {
        if (isMotionSensorRegistered) return
        sensorManager?.let { sm ->
            val accel = sm.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION)
                ?: sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
            accel?.let {
                sm.registerListener(this, it, SensorManager.SENSOR_DELAY_NORMAL)
                isMotionSensorRegistered = true
            }
        }
    }

    @Synchronized
    private fun unregisterMotionSensor() {
        if (!isMotionSensorRegistered) return
        runCatching { sensorManager?.unregisterListener(this) }
        isMotionSensorRegistered = false
    }

    override fun onSensorChanged(event: SensorEvent?) {
        if (event == null) return
        val now = System.currentTimeMillis()
        if (now - lastMovementCheckTime < 2500) return
        lastMovementCheckTime = now

        val x = event.values[0]
        val y = event.values[1]
        val z = event.values[2]
        val magnitude = sqrt(x * x + y * y + z * z)

        val isMoving = if (event.sensor.type == Sensor.TYPE_LINEAR_ACCELERATION) {
            magnitude > 1.2f
        } else {
            kotlin.math.abs(magnitude - 9.8f) > 1.8f
        }

        if (_contextState.value.isMoving != isMoving) {
            _contextState.value = _contextState.value.copy(isMoving = isMoving)
            updateState()
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    private fun updateState() {
        val curr = _contextState.value
        val isCarActive = manualCarModeOverride ?: (curr.isCarOrBluetoothConnected && curr.isMoving)
        val modeLabel = if (isCarActive) {
            "Modo Cockpit Automotivo (Hands-Free)"
        } else if (curr.isCarOrBluetoothConnected) {
            "Modo Fone / Bluetooth (${curr.audioDeviceName ?: "Áudio Ativo"})"
        } else {
            "Cockpit Executivo Padrão"
        }

        _contextState.value = curr.copy(
            isCarModeActive = isCarActive,
            recommendedModeLabel = modeLabel
        )
    }
}
