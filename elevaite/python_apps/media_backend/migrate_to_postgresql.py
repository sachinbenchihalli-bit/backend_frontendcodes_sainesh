#!/usr/bin/env python3
"""
Migration script to create PostgreSQL tables for session management
and optionally migrate existing Redis data to PostgreSQL.

This script:
1. Creates the new PostgreSQL tables for session management
2. Optionally migrates existing Redis data to PostgreSQL
3. Provides verification of the migration
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from db_connector import db_connector
from database_models import (
    SessionModel, QueryModel, AgentExecutionStepModel,
    FeedbackModel
)
from cache_control import CacheControl
from model import (
    FeedbackData, VotingData, AgentExecutionStep, QueryExecutionData,
    SessionMetadata, FeedbackType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLMigration:
    """Handles migration from Redis to PostgreSQL for session management"""

    def __init__(self):
        self.db_connector = db_connector
        try:
            self.redis_cache = CacheControl()
            self.redis_available = True
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self.redis_available = False

    def create_tables(self):
        """Create all PostgreSQL tables"""
        try:
            logger.info("Creating PostgreSQL tables...")
            self.db_connector.create_tables()
            logger.info("PostgreSQL tables created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            return False

    def verify_tables(self):
        """Verify that all tables were created"""
        try:
            db_session = self.db_connector.get_session()

            # Check if tables exist by trying to query them
            tables_to_check = [
                SessionModel, QueryModel, AgentExecutionStepModel,
                FeedbackModel
            ]

            for table_model in tables_to_check:
                count = db_session.query(table_model).count()
                logger.info(f"Table {table_model.__tablename__}: {count} records")

            db_session.close()
            logger.info("All tables verified successfully")
            return True

        except Exception as e:
            logger.error(f"Error verifying tables: {e}")
            if 'db_session' in locals():
                db_session.close()
            return False

    async def migrate_redis_data(self):
        """Migrate existing Redis data to PostgreSQL"""
        if not self.redis_available:
            logger.warning("Redis not available, skipping data migration")
            return True

        try:
            logger.info("Starting Redis to PostgreSQL data migration...")

            # Migrate sessions
            await self._migrate_sessions()

            # Migrate queries
            await self._migrate_queries()

            # Migrate feedback
            await self._migrate_feedback()

            # Migrate agent performance metrics
            await self._migrate_agent_metrics()

            logger.info("Data migration completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error during data migration: {e}")
            return False

    async def _migrate_sessions(self):
        """Migrate session data from Redis to PostgreSQL"""
        logger.info("Migrating sessions...")

        db_session = self.db_connector.get_session()
        migrated_count = 0

        try:
            # Get all session keys from Redis
            session_keys = []
            for key in self.redis_cache.cache.scan_iter(match="session:*:metadata"):
                session_keys.append(key.decode('utf-8'))

            for session_key in session_keys:
                try:
                    session_json = self.redis_cache.get(session_key)
                    if session_json:
                        session_data = json.loads(session_json.decode('utf-8'))

                        # Check if session already exists
                        existing_session = db_session.query(SessionModel).filter_by(
                            session_id=session_data['session_id']
                        ).first()

                        if not existing_session:
                            session_record = SessionModel(
                                session_id=session_data['session_id'],
                                user_id=session_data['user_id'],
                                session_name=session_data['session_name'],
                                creation_time=datetime.fromisoformat(session_data['creation_time'].replace('Z', '+00:00')),
                                last_activity_time=datetime.fromisoformat(session_data['last_activity_time'].replace('Z', '+00:00')),
                                total_queries=session_data.get('total_queries', 0),
                                topics_discussed=session_data.get('topics_discussed', []),
                                primary_intent=session_data.get('primary_intent'),
                                session_summary=session_data.get('session_summary'),
                                total_tokens_used=session_data.get('total_tokens_used', {}),
                                feedback_count=session_data.get('feedback_count', 0),
                                positive_feedback_count=session_data.get('positive_feedback_count', 0),
                                negative_feedback_count=session_data.get('negative_feedback_count', 0)
                            )

                            db_session.add(session_record)
                            migrated_count += 1

                except Exception as e:
                    logger.error(f"Error migrating session {session_key}: {e}")
                    continue

            db_session.commit()
            logger.info(f"Migrated {migrated_count} sessions")

        except Exception as e:
            logger.error(f"Error in session migration: {e}")
            db_session.rollback()
        finally:
            db_session.close()

    async def _migrate_queries(self):
        """Migrate query execution data from Redis to PostgreSQL"""
        logger.info("Migrating queries...")

        db_session = self.db_connector.get_session()
        migrated_count = 0

        try:
            # Get all query keys from Redis
            query_keys = []
            for key in self.redis_cache.cache.scan_iter(match="query:*:metadata"):
                query_keys.append(key.decode('utf-8'))

            for query_key in query_keys:
                try:
                    query_json = self.redis_cache.get(query_key)
                    if query_json:
                        query_data = json.loads(query_json.decode('utf-8'))

                        # Check if query already exists
                        existing_query = db_session.query(QueryModel).filter_by(
                            query_id=query_data['query_id']
                        ).first()

                        if not existing_query:
                            query_record = QueryModel(
                                query_id=query_data['query_id'],
                                session_id=query_data['session_id'],
                                user_id=query_data['user_id'],
                                original_query=query_data['original_query'],
                                start_time=datetime.fromisoformat(query_data['start_time'].replace('Z', '+00:00')),
                                end_time=datetime.fromisoformat(query_data['end_time'].replace('Z', '+00:00')) if query_data.get('end_time') else None,
                                total_duration_ms=query_data.get('total_duration_ms'),
                                final_response=query_data.get('final_response', ''),
                                intent_detected=query_data.get('intent_detected'),
                                agents_used=query_data.get('agents_used', []),
                                total_tokens_used=query_data.get('total_tokens_used', {}),
                                success=query_data.get('success', True),
                                error_details=query_data.get('error_details')
                            )

                            db_session.add(query_record)

                            # Migrate execution steps
                            for step_data in query_data.get('execution_steps', []):
                                step_record = AgentExecutionStepModel(
                                    query_id=query_data['query_id'],
                                    agent_name=step_data['agent_name'],
                                    step_type=step_data['step_type'],
                                    start_time=datetime.fromisoformat(step_data['start_time'].replace('Z', '+00:00')),
                                    end_time=datetime.fromisoformat(step_data['end_time'].replace('Z', '+00:00')) if step_data.get('end_time') else None,
                                    duration_ms=step_data.get('duration_ms'),
                                    input_prompt=step_data.get('input_prompt'),
                                    output_response=step_data.get('output_response'),
                                    model_used=step_data.get('model_used'),
                                    tokens_used=step_data.get('tokens_used', {}),
                                    success=step_data.get('success', True),
                                    error_details=step_data.get('error_details'),
                                    step_metadata=step_data.get('metadata', {})
                                )
                                db_session.add(step_record)

                            migrated_count += 1

                except Exception as e:
                    logger.error(f"Error migrating query {query_key}: {e}")
                    continue

            db_session.commit()
            logger.info(f"Migrated {migrated_count} queries")

        except Exception as e:
            logger.error(f"Error in query migration: {e}")
            db_session.rollback()
        finally:
            db_session.close()

    async def _migrate_feedback(self):
        """Migrate feedback data from Redis to PostgreSQL"""
        logger.info("Migrating feedback...")

        db_session = self.db_connector.get_session()
        migrated_count = 0

        try:
            # Get all feedback keys from Redis
            feedback_keys = []
            for key in self.redis_cache.cache.scan_iter(match="feedback:*"):
                key_str = key.decode('utf-8')
                # Only process direct feedback keys, not user or session sets
                if ':' in key_str and not key_str.startswith('feedback:user:') and not key_str.startswith('feedback:session:'):
                    feedback_keys.append(key_str)

            for feedback_key in feedback_keys:
                try:
                    feedback_json = self.redis_cache.get(feedback_key)
                    if feedback_json:
                        feedback_data = json.loads(feedback_json.decode('utf-8'))

                        # Check if feedback already exists
                        existing_feedback = db_session.query(FeedbackModel).filter_by(
                            query_id=feedback_data['query_id']
                        ).first()

                        if not existing_feedback:
                            feedback_record = FeedbackModel(
                                query_id=feedback_data['query_id'],
                                session_id=feedback_data['session_id'],
                                user_id=feedback_data['user_id'],
                                feedback_type=feedback_data['feedback_type'],
                                feedback_text=feedback_data.get('feedback_text'),
                                vote=feedback_data.get('vote', 0),
                                timestamp=datetime.fromisoformat(feedback_data['timestamp'].replace('Z', '+00:00')),
                                agent_specific_feedback=feedback_data.get('agent_specific_feedback', {})
                            )

                            db_session.add(feedback_record)
                            migrated_count += 1

                except Exception as e:
                    logger.error(f"Error migrating feedback {feedback_key}: {e}")
                    continue

            db_session.commit()
            logger.info(f"Migrated {migrated_count} feedback records")

        except Exception as e:
            logger.error(f"Error in feedback migration: {e}")
            db_session.rollback()
        finally:
            db_session.close()

    async def _migrate_agent_metrics(self):
        """Migrate agent performance metrics from Redis to PostgreSQL"""
        logger.info("Migrating agent performance metrics...")

        db_session = self.db_connector.get_session()
        migrated_count = 0

        try:
            # Get all agent performance keys from Redis
            agent_keys = []
            for key in self.redis_cache.cache.scan_iter(match="agent:*:performance"):
                agent_keys.append(key.decode('utf-8'))

            for agent_key in agent_keys:
                try:
                    agent_json = self.redis_cache.get(agent_key)
                    if agent_json:
                        agent_data = json.loads(agent_json.decode('utf-8'))

                        # Check if metrics already exist
                        existing_metrics = db_session.query(AgentPerformanceMetricsModel).filter_by(
                            agent_name=agent_data['agent_name']
                        ).first()

                        if not existing_metrics:
                            metrics_record = AgentPerformanceMetricsModel(
                                agent_name=agent_data['agent_name'],
                                date=datetime.fromisoformat(agent_data['last_updated'].replace('Z', '+00:00')),
                                total_executions=agent_data.get('total_executions', 0),
                                successful_executions=agent_data.get('successful_executions', 0),
                                failed_executions=agent_data.get('failed_executions', 0),
                                average_duration_ms=agent_data.get('average_duration_ms'),
                                total_tokens_used=agent_data.get('total_tokens_used', {}),
                                positive_feedback_count=agent_data.get('positive_feedback', 0),
                                negative_feedback_count=agent_data.get('negative_feedback', 0),
                                last_updated=datetime.fromisoformat(agent_data['last_updated'].replace('Z', '+00:00'))
                            )

                            db_session.add(metrics_record)
                            migrated_count += 1

                except Exception as e:
                    logger.error(f"Error migrating agent metrics {agent_key}: {e}")
                    continue

            db_session.commit()
            logger.info(f"Migrated {migrated_count} agent performance metrics")

        except Exception as e:
            logger.error(f"Error in agent metrics migration: {e}")
            db_session.rollback()
        finally:
            db_session.close()


async def main():
    """Main migration function"""
    migration = PostgreSQLMigration()

    print("PostgreSQL Session Management Migration")
    print("=" * 50)

    # Step 1: Create tables
    print("\n1. Creating PostgreSQL tables...")
    if not migration.create_tables():
        print("❌ Failed to create tables")
        return False
    print("✅ Tables created successfully")

    # Step 2: Verify tables
    print("\n2. Verifying tables...")
    if not migration.verify_tables():
        print("❌ Failed to verify tables")
        return False
    print("✅ Tables verified successfully")

    # Step 3: Migrate data (optional)
    if migration.redis_available:
        response = input("\n3. Do you want to migrate existing Redis data? (y/n): ")
        if response.lower() == 'y':
            print("Migrating Redis data to PostgreSQL...")
            if await migration.migrate_redis_data():
                print("✅ Data migration completed successfully")
            else:
                print("❌ Data migration failed")
                return False
        else:
            print("⏭️  Skipping data migration")
    else:
        print("\n3. ⏭️  Redis not available, skipping data migration")

    print("\n🎉 Migration completed successfully!")
    print("\nNext steps:")
    print("1. Update your application to use the new PostgreSQL session manager")
    print("2. Test the new session management functionality")
    print("3. Consider backing up and removing old Redis data once verified")

    return True


if __name__ == "__main__":
    asyncio.run(main())
