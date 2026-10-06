package com.example.aurapostoassitance.ui.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.aurapostoassitance.data.local.ChatSessionEntity
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraDarkBackground
import com.example.aurapostoassitance.ui.theme.AuraDarkSurface
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple
import dev.jeziellago.compose.markdowntext.MarkdownText

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    onNavigateBack: () -> Unit,
    initialQuery: String? = null,
    viewModel: ChatViewModel = hiltViewModel()
) {
    val messages by viewModel.messages.collectAsState()
    val isTyping by viewModel.isAuraTyping.collectAsState()
    val auraStatusMessage by viewModel.auraStatusMessage.collectAsState()
    val sessionTitle by viewModel.currentSessionTitle.collectAsState()
    val sessions by viewModel.sessions.collectAsState()

    // PRE-FILL ONLY, NO AUTOMATIC AI CALLS!
    var inputText by remember { mutableStateOf(initialQuery ?: "") }
    var showMenu by remember { mutableStateOf(false) }
    var showSessionsSheet by remember { mutableStateOf(false) }

    val listState = rememberLazyListState()

    // Auto-scroll to bottom when new messages arrive
    LaunchedEffect(messages.size, messages.lastOrNull()?.text) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column(modifier = Modifier.clickable { showSessionsSheet = true }) {
                        Text(
                            text = sessionTitle,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = AuraEmerald
                        )
                        Text(
                            text = "Toque para alternar chats",
                            style = MaterialTheme.typography.labelSmall,
                            color = Color.Gray
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Voltar",
                            tint = AuraEmerald
                        )
                    }
                },
                actions = {
                    // Button to create a new blank chat
                    IconButton(onClick = { viewModel.createNewChat("Novo Chat") }) {
                        Icon(
                            imageVector = Icons.Default.Add,
                            contentDescription = "Novo Chat",
                            tint = AuraCyan
                        )
                    }
                    // More options menu
                    IconButton(onClick = { showMenu = true }) {
                        Icon(
                            imageVector = Icons.Default.MoreVert,
                            contentDescription = "Opções",
                            tint = Color.White
                        )
                    }
                    DropdownMenu(
                        expanded = showMenu,
                        onDismissRequest = { showMenu = false }
                    ) {
                        DropdownMenuItem(
                            text = { Text("🧹 Limpar este Chat") },
                            onClick = {
                                viewModel.clearCurrentChat()
                                showMenu = false
                            }
                        )
                        DropdownMenuItem(
                            text = { Text("➕ Criar Novo Chat") },
                            onClick = {
                                viewModel.createNewChat("Novo Chat")
                                showMenu = false
                            }
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = AuraDarkSurface
                )
            )
        },
        bottomBar = {
            ChatInputBar(
                text = inputText,
                onTextChange = { inputText = it },
                onSend = {
                    if (inputText.isNotBlank()) {
                        val textToSend = inputText
                        inputText = ""
                        // USER EXPLICITLY SENDS MESSAGE
                        viewModel.sendMessage(textToSend)
                    }
                },
                isTyping = isTyping
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(AuraDarkBackground)
                .padding(paddingValues)
        ) {
            if (messages.isEmpty() && !isTyping) {
                // Empty state guidance
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Text(
                        text = "💬 " + sessionTitle,
                        style = MaterialTheme.typography.headlineSmall,
                        color = AuraEmerald,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Digite sua dúvida ou comando abaixo para consultar a AURA.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.Gray,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                }
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 16.dp),
                    contentPadding = PaddingValues(vertical = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    items(messages, key = { it.id }) { message ->
                        MessageBubble(message)
                    }
                    if (isTyping || auraStatusMessage != null) {
                        item {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier
                                    .padding(start = 8.dp, top = 4.dp, bottom = 8.dp)
                                    .background(
                                        color = AuraDarkSurface,
                                        shape = RoundedCornerShape(12.dp)
                                    )
                                    .padding(horizontal = 12.dp, vertical = 8.dp)
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(16.dp),
                                    color = AuraEmerald,
                                    strokeWidth = 2.dp
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = auraStatusMessage ?: "AURA está raciocinando...",
                                    style = MaterialTheme.typography.labelMedium,
                                    color = AuraCyan,
                                    fontWeight = FontWeight.SemiBold
                                )
                            }
                        }
                    }
                }
            }

            // BottomSheet for switching chat sessions
            if (showSessionsSheet) {
                ModalBottomSheet(
                    onDismissRequest = { showSessionsSheet = false },
                    containerColor = AuraDarkSurface
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(24.dp)
                    ) {
                        Text(
                            text = "Histórico de Chats",
                            style = MaterialTheme.typography.titleLarge,
                            color = AuraEmerald,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(bottom = 16.dp)
                        )

                        Button(
                            onClick = {
                                viewModel.createNewChat("Novo Chat")
                                showSessionsSheet = false
                            },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = AuraEmerald)
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Criar Novo Chat")
                        }

                        Spacer(modifier = Modifier.height(16.dp))

                        LazyColumn(
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            items(sessions) { session ->
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .background(
                                            color = AuraDarkBackground,
                                            shape = RoundedCornerShape(8.dp)
                                        )
                                        .clickable {
                                            viewModel.loadSession(session.sessionId, session.title)
                                            showSessionsSheet = false
                                        }
                                        .padding(16.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(
                                        text = session.title,
                                        style = MaterialTheme.typography.bodyLarge,
                                        color = Color.White,
                                        fontWeight = FontWeight.Medium
                                    )
                                    IconButton(
                                        onClick = { viewModel.deleteSession(session.sessionId) },
                                        modifier = Modifier.size(24.dp)
                                    ) {
                                        Icon(
                                            Icons.Default.Delete,
                                            contentDescription = "Excluir",
                                            tint = Color.Gray
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun MessageBubble(message: ChatMessage) {
    val isUser = message.isFromUser
    val alignment = if (isUser) Alignment.CenterEnd else Alignment.CenterStart
    val shape = if (isUser) {
        RoundedCornerShape(18.dp, 18.dp, 4.dp, 18.dp)
    } else {
        RoundedCornerShape(18.dp, 18.dp, 18.dp, 4.dp)
    }

    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = alignment
    ) {
        Column(
            modifier = Modifier
                .widthIn(max = 340.dp)
                .background(
                    color = if (isUser) AuraPurple.copy(alpha = 0.25f) else AuraDarkSurface,
                    shape = shape
                )
                .border(
                    width = 1.dp,
                    color = if (isUser) AuraPurple.copy(alpha = 0.4f) else AuraEmerald.copy(alpha = 0.3f),
                    shape = shape
                )
                .padding(16.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(bottom = 6.dp)
            ) {
                Text(
                    text = if (isUser) "👤 Você" else "🤖 AURA",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = if (isUser) AuraPurple else AuraEmerald
                )
            }

            if (isUser) {
                Text(
                    text = message.text,
                    style = MaterialTheme.typography.bodyLarge,
                    color = Color.White
                )
            } else {
                // Enhanced Markdown rendering for AI reports
                val formattedMarkdown = AuraMarkupFormatter.format(message.text)
                MarkdownText(
                    markdown = formattedMarkdown,
                    style = MaterialTheme.typography.bodyLarge.copy(
                        color = Color.White,
                        lineHeight = MaterialTheme.typography.bodyLarge.lineHeight * 1.25f
                    ),
                    linkColor = AuraCyan
                )
            }
        }
    }
}

@Composable
fun ChatInputBar(
    text: String,
    onTextChange: (String) -> Unit,
    onSend: () -> Unit,
    isTyping: Boolean
) {
    Surface(
        color = AuraDarkSurface,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .padding(horizontal = 16.dp, vertical = 10.dp)
                .navigationBarsPadding(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = text,
                onValueChange = onTextChange,
                modifier = Modifier
                    .weight(1f)
                    .padding(end = 8.dp),
                placeholder = { Text("Peça um diagnóstico...", color = Color.Gray) },
                shape = RoundedCornerShape(24.dp),
                maxLines = 4,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = AuraEmerald,
                    unfocusedBorderColor = Color.Gray.copy(alpha = 0.5f),
                    focusedContainerColor = AuraDarkBackground,
                    unfocusedContainerColor = AuraDarkBackground
                )
            )

            FloatingActionButton(
                onClick = onSend,
                containerColor = if (text.isNotBlank()) AuraEmerald else Color.Gray.copy(alpha = 0.5f),
                contentColor = Color.White,
                shape = RoundedCornerShape(50),
                modifier = Modifier.size(48.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Send,
                    contentDescription = "Enviar",
                    modifier = Modifier.size(22.dp)
                )
            }
        }
    }
}
