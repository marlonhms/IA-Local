package com.example.aurapostoassitance

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.fragment.app.FragmentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
import androidx.compose.animation.scaleOut
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.lifecycle.lifecycleScope
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.aurapostoassitance.data.vision.AuraSharedIntakeRelay
import com.example.aurapostoassitance.data.vision.SharedDocumentPayload
import com.example.aurapostoassitance.ui.chat.ChatScreen
import com.example.aurapostoassitance.ui.dashboard.DashboardScreen
import com.example.aurapostoassitance.ui.setup.SetupScreen
import com.example.aurapostoassitance.ui.entrance.AuraEntranceScreen
import com.example.aurapostoassitance.ui.theme.AuraPostoAssitanceTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.File
import java.io.FileOutputStream
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : FragmentActivity() {

    @Inject
    lateinit var sharedIntakeRelay: AuraSharedIntakeRelay

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIncomingDocumentIntent(intent)
    }

    private fun handleIncomingDocumentIntent(incomingIntent: Intent?) {
        val action = incomingIntent?.action ?: return
        val incomingUri: Uri? = when (action) {
            Intent.ACTION_SEND -> {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    incomingIntent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    incomingIntent.getParcelableExtra(Intent.EXTRA_STREAM)
                }
            }
            Intent.ACTION_VIEW -> incomingIntent.data
            else -> null
        }
        if (incomingUri == null) return

        val declaredMime = incomingIntent.type ?: contentResolver.getType(incomingUri) ?: "application/octet-stream"
        val stream = runCatching { contentResolver.openInputStream(incomingUri) }.getOrNull() ?: return

        lifecycleScope.launch(Dispatchers.IO) {
            runCatching {
                val inboxDir = File(cacheDir, "shared_inbox").apply { mkdirs() }
                val ext = when {
                    declaredMime.contains("pdf") -> "pdf"
                    declaredMime.contains("xml") -> "xml"
                    declaredMime.contains("png") -> "png"
                    else -> "jpg"
                }
                val fileName = "shared_${System.currentTimeMillis()}.$ext"
                val destFile = File(inboxDir, fileName)
                stream.use { input ->
                    FileOutputStream(destFile).use { output ->
                        input.copyTo(output)
                    }
                }
                sharedIntakeRelay.publish(
                    SharedDocumentPayload(
                        id = System.currentTimeMillis().toString(),
                        localUri = Uri.fromFile(destFile),
                        mimeType = declaredMime,
                        fileName = incomingUri.lastPathSegment ?: fileName
                    )
                )
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT)
        )
        if (savedInstanceState == null) {
            handleIncomingDocumentIntent(intent)
        }
        setContent {
            AuraPostoAssitanceTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()
                    val pendingSharedDoc by sharedIntakeRelay.pendingDocument.collectAsState()

                    val shortcutQuery = remember { intent?.getStringExtra("aura_query") }
                    val shortcutAction = remember { intent?.getStringExtra("aura_shortcut_action") }

                    LaunchedEffect(pendingSharedDoc?.id) {
                        if (pendingSharedDoc != null) {
                            navController.navigate("chat") {
                                popUpTo("entrance") { inclusive = true }
                                launchSingleTop = true
                            }
                        }
                    }

                    LaunchedEffect(shortcutQuery, shortcutAction) {
                        if (!shortcutQuery.isNullOrBlank()) {
                            navController.navigate("chat?query=$shortcutQuery") {
                                popUpTo("entrance") { inclusive = true }
                            }
                        } else if (shortcutAction == "play_briefing") {
                            navController.navigate("dashboard") {
                                popUpTo("entrance") { inclusive = true }
                            }
                        }
                    }

                    NavHost(
                        navController = navController,
                        startDestination = "entrance",
                        enterTransition = {
                            fadeIn(animationSpec = tween(300)) + scaleIn(
                                initialScale = 0.96f,
                                animationSpec = tween(350, easing = FastOutSlowInEasing)
                            )
                        },
                        exitTransition = {
                            fadeOut(animationSpec = tween(250)) + scaleOut(
                                targetScale = 0.96f,
                                animationSpec = tween(280)
                            )
                        },
                        popEnterTransition = {
                            fadeIn(animationSpec = tween(300)) + scaleIn(
                                initialScale = 0.96f,
                                animationSpec = tween(350, easing = FastOutSlowInEasing)
                            )
                        },
                        popExitTransition = {
                            fadeOut(animationSpec = tween(250)) + scaleOut(
                                targetScale = 0.96f,
                                animationSpec = tween(280)
                            )
                        }
                    ) {
                                                composable(
                            route = "entrance",
                            exitTransition = {
                                fadeOut(animationSpec = tween(350)) + scaleOut(
                                    targetScale = 1.06f,
                                    animationSpec = tween(400, easing = FastOutSlowInEasing)
                                )
                            }
                        ) {
                            AuraEntranceScreen(
                                onNavigateToDashboard = {
                                    navController.navigate("dashboard") {
                                        popUpTo("entrance") { inclusive = true }
                                    }
                                },
                                onNavigateToSetup = {
                                    navController.navigate("setup") {
                                        popUpTo("entrance") { inclusive = true }
                                    }
                                }
                            )
                        }

composable(
                            route = "setup",
                            exitTransition = {
                                fadeOut(animationSpec = tween(250)) + scaleOut(
                                    targetScale = 0.94f,
                                    animationSpec = tween(280, easing = FastOutSlowInEasing)
                                )
                            }
                        ) {
                            SetupScreen(
                                onSetupComplete = {
                                    navController.navigate("dashboard") {
                                        popUpTo("setup") { inclusive = true }
                                    }
                                }
                            )
                        }

                        composable(
                            route = "dashboard",
                            enterTransition = {
                                fadeIn(animationSpec = tween(350)) + scaleIn(
                                    initialScale = 0.95f,
                                    animationSpec = tween(380, easing = FastOutSlowInEasing)
                                )
                            },
                            exitTransition = {
                                fadeOut(animationSpec = tween(250)) + slideOutOfContainer(
                                    towards = AnimatedContentTransitionScope.SlideDirection.Start,
                                    animationSpec = tween(320, easing = FastOutSlowInEasing)
                                )
                            },
                            popEnterTransition = {
                                fadeIn(animationSpec = tween(300)) + slideIntoContainer(
                                    towards = AnimatedContentTransitionScope.SlideDirection.End,
                                    animationSpec = tween(340, easing = FastOutSlowInEasing)
                                )
                            }
                        ) {
                            DashboardScreen(
                                onNavigateToChat = { initialQuery ->
                                    if (initialQuery != null) {
                                        navController.navigate("chat?query=$initialQuery")
                                    } else {
                                        navController.navigate("chat")
                                    }
                                },
                                onNavigateToSetup = {
                                    navController.navigate("setup")
                                }
                            )
                        }

                        composable(
                            route = "chat?query={query}",
                            arguments = listOf(
                                navArgument("query") {
                                    nullable = true
                                    defaultValue = null
                                }
                            ),
                            enterTransition = {
                                fadeIn(animationSpec = tween(320)) + slideIntoContainer(
                                    towards = AnimatedContentTransitionScope.SlideDirection.Start,
                                    animationSpec = tween(360, easing = FastOutSlowInEasing)
                                )
                            },
                            popExitTransition = {
                                fadeOut(animationSpec = tween(250)) + slideOutOfContainer(
                                    towards = AnimatedContentTransitionScope.SlideDirection.End,
                                    animationSpec = tween(320, easing = FastOutSlowInEasing)
                                )
                            }
                        ) { backStackEntry ->
                            val initialQuery = backStackEntry.arguments?.getString("query")
                            ChatScreen(
                                onNavigateBack = {
                                    navController.popBackStack()
                                },
                                initialQuery = initialQuery
                            )
                        }
                    }
                }
            }
        }
    }
}
