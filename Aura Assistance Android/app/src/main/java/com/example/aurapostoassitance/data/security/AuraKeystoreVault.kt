package com.example.aurapostoassitance.data.security

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.example.aurapostoassitance.data.remote.AuraAuthCredentialsProvider
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Cofre criptográfico nativo baseado em AndroidKeyStore (AES-256-GCM) para armazenar
 * credenciais de rede (X-API-Key, tenant_id, filial_id) sem expor segredos em texto claro
 * e sem exigir dependências externas adicionais.
 */
@Singleton
class AuraKeystoreVault @Inject constructor(
    @ApplicationContext context: Context
) : AuraAuthCredentialsProvider {
    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    private val _authExpiredEvents = MutableSharedFlow<String>(extraBufferCapacity = 4)
    val authExpiredEvents: SharedFlow<String> = _authExpiredEvents.asSharedFlow()

    override fun notifyAuthExpired(reason: String) {
        _authExpiredEvents.tryEmit(reason)
    }

    override fun resolveApiKey(): String? = apiKey

    override fun resolvePartnerApiKey(): String? = partnerApiKey

    var apiKey: String?
        get() = getDecrypted(KEY_API_KEY)
        set(value) {
            if (value.isNullOrBlank()) {
                prefs.edit().remove(KEY_API_KEY).apply()
            } else {
                putEncrypted(KEY_API_KEY, value.trim())
            }
        }

    var partnerApiKey: String?
        get() = getDecrypted(KEY_PARTNER_API_KEY)
        set(value) {
            if (value.isNullOrBlank()) {
                prefs.edit().remove(KEY_PARTNER_API_KEY).apply()
            } else {
                putEncrypted(KEY_PARTNER_API_KEY, value.trim())
            }
        }

    var tenantId: String
        get() = prefs.getString(KEY_TENANT_ID, DEFAULT_TENANT_ID)?.takeIf { it.isNotBlank() }
            ?: DEFAULT_TENANT_ID
        set(value) {
            prefs.edit().putString(KEY_TENANT_ID, value.trim().ifBlank { DEFAULT_TENANT_ID }).apply()
        }

    var filialId: String
        get() = prefs.getString(KEY_FILIAL_ID, DEFAULT_FILIAL_ID)?.takeIf { it.isNotBlank() }
            ?: DEFAULT_FILIAL_ID
        set(value) {
            prefs.edit().putString(KEY_FILIAL_ID, value.trim().ifBlank { DEFAULT_FILIAL_ID }).apply()
        }

    fun hasApiKey(): Boolean = !apiKey.isNullOrBlank()

    private fun getOrCreateSecretKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        val existing = keyStore.getKey(KEY_ALIAS, null) as? SecretKey
        if (existing != null) return existing

        val keyGenerator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        val spec = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build()
        keyGenerator.init(spec)
        return keyGenerator.generateKey()
    }

    private fun putEncrypted(key: String, plainText: String) {
        runCatching {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.ENCRYPT_MODE, getOrCreateSecretKey())
            val iv = cipher.iv
            val encrypted = cipher.doFinal(plainText.toByteArray(Charsets.UTF_8))
            val combined = ByteArray(iv.size + encrypted.size)
            System.arraycopy(iv, 0, combined, 0, iv.size)
            System.arraycopy(encrypted, 0, combined, iv.size, encrypted.size)
            val encoded = Base64.encodeToString(combined, Base64.NO_WRAP)
            prefs.edit().putString(key, encoded).apply()
        }
    }

    private fun getDecrypted(key: String): String? {
        val encoded = prefs.getString(key, null) ?: return null
        return runCatching {
            val combined = Base64.decode(encoded, Base64.NO_WRAP)
            if (combined.size <= GCM_IV_LENGTH) return null
            val iv = combined.copyOfRange(0, GCM_IV_LENGTH)
            val ciphertext = combined.copyOfRange(GCM_IV_LENGTH, combined.size)
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, getOrCreateSecretKey(), GCMParameterSpec(GCM_TAG_BITS, iv))
            String(cipher.doFinal(ciphertext), Charsets.UTF_8).takeIf { it.isNotBlank() }
        }.getOrNull()
    }

    companion object {
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val KEY_ALIAS = "aura_carbon_api_key_v1"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val GCM_IV_LENGTH = 12
        private const val GCM_TAG_BITS = 128
        private const val PREFS_NAME = "aura_keystore_vault"
        private const val KEY_API_KEY = "enc_api_key"
        private const val KEY_PARTNER_API_KEY = "enc_partner_api_key"
        private const val KEY_TENANT_ID = "tenant_id"
        private const val KEY_FILIAL_ID = "filial_id"
        const val DEFAULT_TENANT_ID = "posto_01"
        const val DEFAULT_FILIAL_ID = "59050"
    }
}
