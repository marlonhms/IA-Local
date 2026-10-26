package com.example.aurapostoassitance

import android.os.Bundle
import androidx.activity.ComponentActivity
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
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.example.aurapostoassitance.ui.chat.ChatScreen
import com.example.aurapostoassitance.ui.dashboard.DashboardScreen
import com.example.aurapostoassitance.ui.setup.SetupScreen
import com.example.aurapostoassitance.ui.theme.AuraPostoAssitanceTheme
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            AuraPostoAssitanceTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()

                    NavHost(
                        navController = navController,
                        startDestination = "setup",
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
