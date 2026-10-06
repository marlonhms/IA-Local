package com.example.aurapostoassitance

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
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
                    
                    NavHost(navController = navController, startDestination = "setup") {
                        composable("setup") {
                            SetupScreen(
                                onSetupComplete = {
                                    navController.navigate("dashboard") {
                                        popUpTo("setup") { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable("dashboard") {
                            DashboardScreen(
                                onNavigateToChat = { initialQuery ->
                                    if (initialQuery != null) {
                                        navController.navigate("chat?query=$initialQuery")
                                    } else {
                                        navController.navigate("chat")
                                    }
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
                            )
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
