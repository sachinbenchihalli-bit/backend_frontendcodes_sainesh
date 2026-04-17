"""
Session Topic Analysis and Auto-Naming Service

This module provides intelligent session naming based on conversation topics
and intent analysis using the existing LLM infrastructure.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from model import SessionTopicAnalysis, ConversationPayload, SessionMetadata
from llm_utils import generate_response
from prompts.prompts import load_prompt

logger = logging.getLogger(__name__)

class SessionTopicAnalyzer:
    """Analyzes session topics and generates intelligent session names"""

    def __init__(self):
        pass

    async def analyze_session_topics(self, session_queries: List[str],
                                   conversation_history: List[ConversationPayload],
                                   query_id: Optional[str] = None) -> SessionTopicAnalysis:
        """
        Analyze session topics and generate a suggested session name

        Args:
            session_queries: List of user queries in the session
            conversation_history: Complete conversation history

        Returns:
            SessionTopicAnalysis with suggested name and topic breakdown
        """
        try:
            # Prepare the analysis prompt
            queries_text = "\n".join([f"- {query}" for query in session_queries])

            # Create conversation context
            conversation_context = ""
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                conversation_context += f"{msg.actor}: {msg.content[:200]}...\n"

            # Use the topic analysis prompt
            analysis_prompt = f"""
            Analyze the following user queries and conversation to identify the main topics discussed and suggest an appropriate session name.

            User Queries:
            {queries_text}

            Recent Conversation Context:
            {conversation_context}

            Please identify:
            1. Primary topics (most important themes)
            2. Secondary topics (supporting themes)
            3. A concise, descriptive session name (max 50 characters)
            4. Confidence score (0.0 to 1.0) for the analysis
            5. Brief reasoning for the suggested name

            Focus on business/marketing themes like:
            - Campaign performance analysis
            - Creative insights and trends
            - Media planning and strategy
            - Brand analysis
            - Industry comparisons
            - Image generation and creative development
            """

            # Generate the analysis using the existing LLM infrastructure
            response = await generate_response(
                query=analysis_prompt,
                system_prompt="You are an expert at analyzing marketing and advertising conversations to identify key topics and create meaningful session names.",
                response_class=SessionTopicAnalysis,
                max_tokens=800,
                model="gpt-4o-mini",
                query_id=query_id,
                agent_name="session_topic_analyzer"
            )

            # Parse the response
            if isinstance(response, str):
                analysis_data = json.loads(response)
                return SessionTopicAnalysis(**analysis_data)
            else:
                return response

        except Exception as e:
            logger.error(f"Error analyzing session topics: {e}")
            # Return a fallback analysis
            return self._create_fallback_analysis(session_queries)

    async def generate_session_name_from_intent(self, primary_intent: str,
                                              key_entities: List[str]) -> str:
        """
        Generate a session name based on detected intent and key entities

        Args:
            primary_intent: The most common intent in the session
            key_entities: Key entities mentioned (brands, industries, etc.)

        Returns:
            Generated session name
        """
        try:
            # Create intent-based naming rules
            intent_templates = {
                "campaign_performance": "Campaign Analysis",
                "creative_insights": "Creative Research",
                "media_planning": "Media Strategy",
                "image_generation": "Creative Development",
                "general_query": "Marketing Discussion"
            }

            base_name = intent_templates.get(primary_intent, "Marketing Session")

            # Add entity context if available
            if key_entities:
                # Take the first 2 most relevant entities
                entity_context = " - " + ", ".join(key_entities[:2])
                max_length = 50 - len(base_name)
                if len(entity_context) <= max_length:
                    base_name += entity_context
                else:
                    # Truncate entities to fit
                    truncated_context = entity_context[:max_length-3] + "..."
                    base_name += truncated_context

            return base_name

        except Exception as e:
            logger.error(f"Error generating session name from intent: {e}")
            return f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    async def extract_key_entities(self, session_queries: List[str], query_id: Optional[str] = None) -> List[str]:
        """
        Extract key entities (brands, industries, products) from session queries

        Args:
            session_queries: List of user queries

        Returns:
            List of key entities mentioned
        """
        try:
            queries_text = " ".join(session_queries)

            entity_prompt = f"""
            Extract the key business entities mentioned in these queries:

            {queries_text}

            Focus on:
            - Brand names (McDonald's, Nike, Coca-Cola, etc.)
            - Industry sectors (Food & Beverage, Fashion, Technology, etc.)
            - Product categories
            - Campaign types or objectives

            Return only the most relevant entities as a JSON list of strings.
            Limit to maximum 5 entities, prioritize by frequency and importance.
            """

            response = await generate_response(
                query=entity_prompt,
                system_prompt="You are an expert at extracting business entities from marketing and advertising queries. Return only a JSON array of strings.",
                max_tokens=200,
                model="gpt-4o-mini",
                query_id=query_id,
                agent_name="entity_extractor"
            )

            # Parse the response
            if isinstance(response, str):
                try:
                    entities = json.loads(response)
                    if isinstance(entities, list):
                        return entities[:5]  # Limit to 5 entities
                except json.JSONDecodeError:
                    logger.warning("Failed to parse entity extraction response as JSON")

            return []

        except Exception as e:
            logger.error(f"Error extracting key entities: {e}")
            return []

    async def update_session_with_topic_analysis(self, session_metadata: SessionMetadata,
                                               new_query: str) -> SessionMetadata:
        """
        Update session metadata with topic analysis from a new query

        Args:
            session_metadata: Current session metadata
            new_query: New query to analyze

        Returns:
            Updated session metadata
        """
        try:
            # Add the new query to the session's query history
            all_queries = session_metadata.query_ids + [new_query]

            # If this is the first few queries, update the session name
            if len(all_queries) <= 3:
                # Extract entities from all queries so far
                entities = await self.extract_key_entities(all_queries)

                # Update session name if we have good entities
                if entities and session_metadata.primary_intent:
                    new_name = await self.generate_session_name_from_intent(
                        session_metadata.primary_intent, entities
                    )
                    session_metadata.session_name = new_name

            # Update topics discussed (simple keyword extraction for now)
            query_topics = await self._extract_simple_topics(new_query)
            for topic in query_topics:
                if topic not in session_metadata.topics_discussed:
                    session_metadata.topics_discussed.append(topic)

            return session_metadata

        except Exception as e:
            logger.error(f"Error updating session with topic analysis: {e}")
            return session_metadata

    def _create_fallback_analysis(self, session_queries: List[str]) -> SessionTopicAnalysis:
        """Create a fallback analysis when the main analysis fails"""
        try:
            # Simple keyword-based analysis
            all_text = " ".join(session_queries).lower()

            primary_topics = []
            secondary_topics = []

            # Define topic keywords
            topic_keywords = {
                "campaign_performance": ["performance", "campaign", "clicks", "conversion", "metrics"],
                "creative_insights": ["creative", "design", "visual", "brand", "imagery"],
                "media_planning": ["media", "plan", "strategy", "budget", "audience"],
                "image_generation": ["generate", "create", "image", "ad", "creative"]
            }

            # Count topic relevance
            topic_scores = {}
            for topic, keywords in topic_keywords.items():
                score = sum(1 for keyword in keywords if keyword in all_text)
                if score > 0:
                    topic_scores[topic] = score

            # Sort topics by relevance
            sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)

            if sorted_topics:
                primary_topics = [sorted_topics[0][0]]
                if len(sorted_topics) > 1:
                    secondary_topics = [topic for topic, _ in sorted_topics[1:3]]

            # Generate simple session name
            if primary_topics:
                suggested_name = primary_topics[0].replace("_", " ").title()
            else:
                suggested_name = f"Session {datetime.now().strftime('%m-%d %H:%M')}"

            return SessionTopicAnalysis(
                primary_topics=primary_topics,
                secondary_topics=secondary_topics,
                suggested_name=suggested_name,
                confidence_score=0.6,  # Medium confidence for fallback
                reasoning="Fallback analysis based on keyword matching"
            )

        except Exception as e:
            logger.error(f"Error creating fallback analysis: {e}")
            return SessionTopicAnalysis(
                primary_topics=[],
                secondary_topics=[],
                suggested_name=f"Session {datetime.now().strftime('%m-%d %H:%M')}",
                confidence_score=0.3,
                reasoning="Error in analysis, using timestamp-based name"
            )

    async def _extract_simple_topics(self, query: str) -> List[str]:
        """Extract simple topics from a query using keyword matching"""
        try:
            query_lower = query.lower()
            topics = []

            # Define topic patterns
            topic_patterns = {
                "campaign_analysis": ["campaign", "performance", "metrics", "analytics"],
                "creative_research": ["creative", "design", "visual", "imagery"],
                "brand_analysis": ["brand", "branding", "logo", "identity"],
                "media_strategy": ["media", "planning", "strategy", "budget"],
                "industry_comparison": ["industry", "sector", "compare", "comparison"],
                "image_creation": ["generate", "create", "image", "picture"]
            }

            for topic, patterns in topic_patterns.items():
                if any(pattern in query_lower for pattern in patterns):
                    topics.append(topic)

            return topics[:3]  # Limit to 3 topics per query

        except Exception as e:
            logger.error(f"Error extracting simple topics: {e}")
            return []
