# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.

# Retrofit & OkHttp
-dontwarn okio.**
-dontwarn okhttp3.**
-dontwarn retrofit2.**
-keep class retrofit2.** { *; }
-keepattributes Signature
-keepattributes Exceptions
-keepattributes *Annotation*

# Kotlinx Serialization
-keepclassmembers class kotlinx.serialization.json.** {
    *** Companion;
}
-keepclasseswithmembers class kotlinx.serialization.json.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# Hilt / Dagger
-keep class dagger.** { *; }
-keep class hilt_aggregated_deps.** { *; }
-dontwarn dagger.**
-keepclassmembers,allowobfuscation class * {
    @javax.inject.* *;
    @dagger.hilt.* *;
}

# Keep Data Classes (Models for API)
# This prevents ProGuard from obfuscating variables that GSON / Serialization use
-keep class com.example.aurapostoassitance.data.remote.** { *; }

# Compose (usually handled automatically by AGP, but good to ensure)
-keep class androidx.compose.** { *; }
