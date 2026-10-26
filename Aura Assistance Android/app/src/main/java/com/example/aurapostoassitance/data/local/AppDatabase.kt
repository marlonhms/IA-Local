package com.example.aurapostoassitance.data.local

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(entities = [ChatMessageEntity::class, ChatSessionEntity::class], version = 4, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun chatDao(): ChatDao
}
