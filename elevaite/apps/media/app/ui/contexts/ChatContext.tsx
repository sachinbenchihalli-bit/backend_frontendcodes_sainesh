"use client";
import { useSession } from "next-auth/react";
import { createContext, useContext, useEffect, useState } from "react";
import { fetchChatbotResponse, fetchSessionSummary } from "../../lib/actions";
import type {
  ChatBotPayload,
  ChatMessageObject,
  ChatMessageResponse,
  ChatbotV,
  SessionObject,
  SessionSummaryObject,
} from "../../lib/interfaces";
import {ChatBotGenAI} from "../../lib/interfaces";
import {
  CHATBOT_MESSAGE_ID_PREFIX,
  SESSION_ID_PREFIX,
  USER_MESSAGE_ID_PREFIX,
  QUERY_ID_PREFIX,
  defaultChatbotV,
  defaultGenAIBotOption,
  defaultSession,
} from "../../lib/interfaces";
import { getLoadingMessageFromAgentStatus } from "./ChatContextHelpers";
// STRUCTURE

export interface ChatContextStructure {
  sessions: SessionObject[];
  addNewSession: () => Promise<void>;
  deleteSessionById: (sessionId: string) => void;
  clearAllSessions: () => void;
  selectedSession: SessionObject | undefined;
  setSelectedSession: (sessionId: string) => void;
  selectedGenAIBot: string |undefined;
  setSelectedGenAIBot: (value: ChatBotGenAI) => void;
  isChatLoading: boolean;
  chatLoadingMessage: string;
  isSessionLoading: boolean;
  addNewUserMessageToCurrentSession: (message: string) => void;
  updateMessageVote: (messageId: string, passedVote: -1 | 0 | 1) => Promise<void>;
  updateMessageFeedback: (messageId: string, passedFeedback: string) => Promise<void>;
  getSessionSummary: () => void;
  removeExpectedDisplayFromSelectedSessionSummary: () => void;
  addNewUserMessageWithLastMessages: (message: string,file?: File) => void;
  addNewBotMessage: (messageText: string) => void;
  loadUserSessions: () => Promise<void>;
  loadSessionDetails: (sessionId: string) => Promise<void>;
  setInsertionOrderLoading: (loading: boolean, message?: string) => void;
}

export const ChatContext = createContext<ChatContextStructure>({
  sessions: [],
  addNewSession: async () => {
    /**/
  },
  deleteSessionById: () => {
    /**/
  },
  clearAllSessions: () => {
    /**/
  },
  selectedSession: undefined,
  setSelectedSession: () => {
    /**/
  },
  selectedGenAIBot:undefined,
  setSelectedGenAIBot: () => {
    /**/
  },
  isChatLoading: false,
  chatLoadingMessage: "",
  isSessionLoading: false,
  addNewUserMessageToCurrentSession: () => {
    /**/
  },
  updateMessageVote: async () => {
    /**/
  },
  updateMessageFeedback: async () => {
    /**/
  },
  getSessionSummary: () => {
    /**/
  },
  removeExpectedDisplayFromSelectedSessionSummary: () => {
    /**/
  },
  addNewUserMessageWithLastMessages: () => {
    /**/
  },
  addNewBotMessage: () => {
    /**/
  },
  loadUserSessions: async () => {
    /**/
  },
  loadSessionDetails: async () => {
    /**/
  },
  setInsertionOrderLoading: () => {
    /**/
  },
});

// PROVIDER

interface ChatContextProviderProps {
  children: React.ReactNode;
}

export function ChatContextProvider(
  props: ChatContextProviderProps
): JSX.Element {
  const session = useSession();
  const [sessions, setSessions] = useState<SessionObject[]>([defaultSession]);
  const [selectedSession, setSelectedSession] = useState<SessionObject>();
  const [selectedGenAIBot, setSelectedGenAIBot] = useState<ChatBotGenAI>(
    defaultGenAIBotOption
  );
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- No provisions to change this for now. Leaving it because we will, eventually.
  const [selectedChatbotV, setSelectedChatbotV] =
    useState<ChatbotV>(defaultChatbotV);
  const [isChatLoading, setIsChatLoading] = useState<boolean>(false);
  const [chatLoadingMessage, setChatLoadingMessage] = useState<string>("");
  const [isSessionLoading, setIsSessionLoading] = useState<boolean>(false);
  const [isCreatingSession, setIsCreatingSession] = useState<boolean>(false);

  // Generate a unique query ID with better collision resistance
  const generateQueryId = () => {
    const timestamp = new Date().getTime();
    const randomPart = Math.floor(Math.random() * 1000000); // Increased from 10000 to 1000000
    const microTime = performance.now().toString().replace('.', ''); // Add microsecond precision
    return `${QUERY_ID_PREFIX}${timestamp}_${randomPart}_${microTime.slice(-6)}`;
  };

  // Helper function to create a new session object with unique ID
  async function createNewSessionObject(): Promise<SessionObject> {
    // Generate a truly unique session ID using timestamp and random component
    const timestamp = new Date().getTime();
    const randomPart = Math.floor(Math.random() * 10000);
    const newId = `${SESSION_ID_PREFIX}${timestamp}_${randomPart}`;

    // Generate a user-friendly session label based on current time
    const now = new Date();
    const sessionLabel = `Session ${now.toLocaleDateString()} ${now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;

    return {
      id: newId,
      label: sessionLabel,
      messages: [],
      creationDate: new Date().toISOString(),
      isNewSession: true,
      hasLoadedMessages: true, // New sessions don't need loading
    };
  }

  // Helper function to create session in backend
  async function createSessionInBackend(sessionObj: SessionObject): Promise<void> {
    // Prevent multiple simultaneous session creation requests
    if (isCreatingSession) {
      console.log('Session creation already in progress, skipping...');
      return;
    }

    try {
      setIsCreatingSession(true);
      const userId = session.data?.user?.email || 
                    session.data?.user?.id || 
                    session.data?.user?.name || 
                    "dev-user";
      const sessionData = {
        session_id: sessionObj.id,
        user_id: userId,
        session_name: sessionObj.label
      };

      const response = await fetch(`${process.env.NEXT_PUBLIC_MEDIA_BACKEND_URL}/session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          "X-Token": "coneofsilence",
        },
        body: JSON.stringify(sessionData)
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Session created in backend:', result);
      } else {
        console.error('Failed to create session in backend:', response.status);
      }
    } catch (error) {
      console.error('Error creating session in backend:', error);
    } finally {
      setIsCreatingSession(false);
    }
  }

  // Load user sessions from backend
  async function loadUserSessions(): Promise<void> {
    try {
      const userId = session.data?.user?.email || 
                    session.data?.user?.id || 
                    session.data?.user?.name || 
                    "dev-user";
      // In development mode, we'll use a fallback user ID if session is null

      const response = await fetch(`${process.env.NEXT_PUBLIC_MEDIA_BACKEND_URL}/sessions/user/${userId}?limit=20`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          "X-Token": "coneofsilence",
        }
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Loaded user sessions:', result);

        // Convert backend sessions to frontend format
        const backendSessions = result.sessions || [];
        const convertedSessions: SessionObject[] = backendSessions.map((backendSession: any) => ({
          id: backendSession.session_id,
          label: backendSession.session_name,
          messages: [], // Will be loaded when session is selected
          creationDate: backendSession.creation_time,
          summary: undefined,
          isNewSession: false, // These are existing sessions from backend
          hasLoadedMessages: false, // Messages need to be loaded
        }));

        // Create a new session for the user (but don't store it in backend yet)
        const newSession = await createNewSessionObject();

        // Set sessions with new session first, then existing sessions
        const allSessions = [newSession, ...convertedSessions];
        setSessions(allSessions);
        setSelectedSession(newSession);

        // NOTE: Don't create the session in backend yet - only when user sends first query
        console.log('New session created in frontend only, will be stored when user sends first query');
      } else {
        console.error('Failed to load user sessions:', response.status);
        // Even if loading fails, create a new session for the user (frontend only)
        const newSession = await createNewSessionObject();
        setSessions([newSession]);
        setSelectedSession(newSession);
        console.log('New session created in frontend only due to loading failure');
      }
    } catch (error) {
      console.error('Error loading user sessions:', error);
      // Even if there's an error, create a new session for the user (frontend only)
      const newSession = await createNewSessionObject();
      setSessions([newSession]);
      setSelectedSession(newSession);
      console.log('New session created in frontend only due to error');
    }
  }

  // Load specific session with full conversation history
  async function loadSessionDetails(sessionId: string): Promise<void> {
    try {
      console.log(`[FRONTEND] Loading session details for: ${sessionId}`);
      const response = await fetch(`${process.env.NEXT_PUBLIC_MEDIA_BACKEND_URL}/session/${sessionId}/full`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          "X-Token": "coneofsilence",
        }
      });

      console.log(`[FRONTEND] Response status: ${response.status}, ok: ${response.ok}`);

      if (response.ok) {
        const result = await response.json();
        console.log('[FRONTEND] Raw response from backend:', result);
        console.log('[FRONTEND] Response type:', typeof result);
        console.log('[FRONTEND] Response keys:', Object.keys(result || {}));

        // Convert query details back to message format
        const messages: ChatMessageObject[] = [];
        const queryDetails = result.query_details || [];

        console.log(`[FRONTEND] Found ${queryDetails.length} query details`);
        console.log('[FRONTEND] Query details structure:', queryDetails);

        for (const query of queryDetails) {
          console.log(`[FRONTEND] Processing query:`, query);
          console.log(`[FRONTEND] Query related_queries:`, query.related_queries);

          // Add user message
          messages.push({
            id: `user-${query.query_id}`,
            userName: session.data?.user?.name ?? "You",
            isBot: false,
            date: query.start_time,
            text: query.original_query,
            query_id: query.query_id
          });

          // Add bot response with related queries
          const botMessage = {
            id: `bot-${query.query_id}`,
            userName: "elevaite",
            isBot: true,
            date: query.end_time || query.start_time,
            text: query.final_response,
            query_id: query.query_id,
            relatedQueries: query.related_queries || []  // Include related queries from database
          };

          console.log(`[FRONTEND] Bot message with related queries:`, botMessage);
          messages.push(botMessage);
        }

        console.log(`[FRONTEND] Converted to ${messages.length} messages:`, messages);

        // Update the sessions array first
        const updatedSessions = sessions.map(session =>
          session.id === sessionId
            ? { ...session, messages, hasLoadedMessages: true }
            : session
        );
        setSessions(updatedSessions);
        console.log(`[FRONTEND] Updated sessions array`);

        // Find the updated session and set it as selected
        const updatedSession = updatedSessions.find(s => s.id === sessionId);
        if (updatedSession) {
          console.log(`[FRONTEND] Found updated session with ${updatedSession.messages.length} messages`);
          setSelectedSession(updatedSession);
          console.log(`[FRONTEND] setSelectedSession called with updated session`);
        } else {
          console.log(`[FRONTEND] Could not find updated session with id: ${sessionId}`);
        }
      } else {
        console.error('[FRONTEND] Failed to load session details:', response.status);
        const errorText = await response.text();
        console.error('[FRONTEND] Error response body:', errorText);
      }
    } catch (error) {
      console.error('[FRONTEND] Error loading session details:', error);
    } finally {
      // Always reset the loading state when done
      setIsSessionLoading(false);
    }
  }
  // Initializations
  // useEffect(() => {
  //     console.log("Sessions changed", sessions);
  // }, [sessions]);

  // const scrollPosition = chatContainerRef.current?.scrollTop;

  // useEffect(() => {
  //   if (chatContainerRef.current && scrollPosition !== undefined) {
  //     chatContainerRef.current.scrollTop = scrollPosition;
  //   }
  // }, [selectedSession?.messages]);

  // Load user sessions when the app starts and user is authenticated
  useEffect(() => {
    // In development mode, session might be null, so we provide a fallback
    const userId = session.data?.user?.email || 
                  session.data?.user?.id || 
                  session.data?.user?.name;
    const isDevelopment = process.env.NODE_ENV === "development";

    if (userId || isDevelopment) {
      loadUserSessions();
    }
  }, [session.data?.user?.email, session.data?.user?.id, session.data?.user?.name, session.status]);

  useEffect(() => {
    if (!selectedGenAIBot) return;
    setSelectedGenAIBot(selectedGenAIBot);
    // console.log("Setting Gen AI Bot:",selectedGenAIBot);
  }, [selectedGenAIBot]);

  // Removed problematic useEffect that was causing circular updates
  // This was interfering with session loading by resetting sessions when selectedSession changed
  // useEffect(() => {
  //   if (!selectedSession) return;
  //   const newSessions = sessions.map((item) =>
  //     item.id === selectedSession.id ? selectedSession : item
  //   );
  //   setSessions(newSessions);
  // }, [selectedSession]);

  useEffect(() => {
    // Only handle the case where all sessions are deleted
    // Don't auto-select sessions when they're being loaded from backend
    if (sessions.length === 0) {
      const newSessions = [defaultSession];
      setSessions(newSessions);
      setSelectedSession(newSessions[0]);
      console.log('Default session created in frontend only, will be stored when user sends first query');
    } else if (sessions.length > 0 && !selectedSession) {
      // Only auto-select if no session is currently selected
      setSelectedSession(sessions[0]);
    }
  }, [sessions.length]);

  async function addNewSession(): Promise<void> {
    // Create new session object (frontend only initially)
    const newSession = await createNewSessionObject();

    // Add it to the list - session will be created in backend when user sends first query
    setSessions((currentSessions) => [...currentSessions, newSession]);

    console.log('New session created in frontend only, will be stored when user sends first query');
  }

  function deleteSessionById(sessionId: string): void {
    const foundSession = sessions.find((item) => item.id === sessionId);
    if (!foundSession) return;
    setSessions((current) =>
      current.filter((item) => {
        return item.id !== sessionId;
      })
    );
  }

  function clearAllSessions(): void {
    setSessions([]);
  }

  function setInternallySelectedSession(sessionId: string): void {
    console.log(`[CONTEXT] setInternallySelectedSession called with sessionId: ${sessionId}`);
    if (!sessionId || sessionId === selectedSession?.id) return;
    const foundSession = sessions.find((item) => item.id === sessionId);
    if (!foundSession) return;

    console.log(`[CONTEXT] Found session:`, foundSession);
    console.log(`[CONTEXT] Session hasLoadedMessages: ${foundSession.hasLoadedMessages}, isNewSession: ${foundSession.isNewSession}`);

    // Set the session immediately for UI responsiveness
    setSelectedSession(foundSession);
    console.log(`[CONTEXT] Set selectedSession to:`, foundSession);

    // Load session details if the session hasn't loaded messages yet
    // Only load for existing sessions that haven't been loaded
    if (!foundSession.hasLoadedMessages && !foundSession.isNewSession) {
      console.log(`[CONTEXT] Starting to load session details for: ${sessionId}`);
      setIsSessionLoading(true);
      loadSessionDetails(sessionId);
    }
  }

  function addNewUserMessageToCurrentSession(messageText: string): void {
    if (!messageText || !selectedSession) return;
    // Find highest id of non-bot messages
    const userIdNumbersList = selectedSession.messages
      .filter((item) => !item.isBot)
      .map((userItem) =>
        Number(userItem.id.slice(USER_MESSAGE_ID_PREFIX.length))
      );
    const newId =
      USER_MESSAGE_ID_PREFIX +
      (userIdNumbersList.length > 0
        ? Math.max(...userIdNumbersList) + 1
        : 0
      ).toString();
    const newMessage: ChatMessageObject = {
      id: newId,
      date: new Date().toISOString(),
      isBot: false,
      userName: session.data?.user?.name ?? "You",
      text: messageText,
    };
    const newSession = updateSessionListWithNewMessage(
      newMessage,
      selectedSession
    );
    void getServerChatbotResponse(messageText, newSession);
  }

  function updateSessionListWithNewMessage(
    message: ChatMessageObject,
    passedSession: SessionObject
  ): SessionObject {
    const newMessageList = [...passedSession.messages, message];
    // If this is the first user message in a new session, mark it as no longer new
    const isFirstUserMessage = !message.isBot && passedSession.isNewSession && newMessageList.filter(m => !m.isBot).length === 1;
    const newSelectedSession = {
      ...passedSession,
      messages: newMessageList,
      isNewSession: isFirstUserMessage ? false : passedSession.isNewSession
    };

    // If this is the first user message in a new session, create it in the backend now
    if (isFirstUserMessage) {
      console.log('First user message detected, creating session in backend:', newSelectedSession.id);
      createSessionInBackend(newSelectedSession).catch(error => {
        console.error('Failed to create session in backend after first message:', error);
      });
    }

    // Update both selectedSession and sessions array for consistency
    setSelectedSession(newSelectedSession);

    // Update the sessions array to keep it in sync
    const updatedSessions = sessions.map(session =>
      session.id === passedSession.id ? newSelectedSession : session
    );
    setSessions(updatedSessions);

    return newSelectedSession;
  }

  async function updateMessageVote(messageId: string, passedVote: -1 | 0 | 1): Promise<void> {
    if (!selectedSession) return;

    // Find the message to get its query_id
    const message = selectedSession.messages.find(msg => msg.id === messageId);
    
    if (!message || !message.query_id) {
      console.warn("Message or query_id not found for voting", { message, messageId });
      return;
    }

    // Update UI immediately for better UX
    const newMessageList = [...selectedSession.messages].map((item) =>
      item.id === messageId ? { ...item, vote: passedVote } : item
    );
    const newSelectedSession = { ...selectedSession, messages: newMessageList };
    setSelectedSession(newSelectedSession);

    // Send vote to backend (following Arlo pattern)
    try {
      const userId = session.data?.user?.email || 
                    session.data?.user?.id || 
                    session.data?.user?.name || 
                    "dev-user";
      const voteData = {
        query_id: message.query_id,
        user_id: userId,
        session_id: selectedSession.id,
        vote: passedVote
      };

      const response = await fetch(`${process.env.NEXT_PUBLIC_MEDIA_BACKEND_URL}/voting`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          "X-Token": "coneofsilence",
        },
        body: JSON.stringify(voteData)
      });

      if (!response.ok) {
        console.error('Failed to submit vote:', response.status);
        // Optionally revert UI change on failure
      } else {
        const result = await response.json();
        console.log('Vote submitted:', result.message);
      }
    } catch (error) {
      console.error('Error submitting vote:', error);
      // Optionally revert UI change on failure
    }
  }

  async function updateMessageFeedback(
    messageId: string,
    passedFeedback: string
  ): Promise<void> {
    if (!selectedSession || !passedFeedback.trim()) return;

    // Find the message to get its query_id and current vote
    const message = selectedSession.messages.find(msg => msg.id === messageId);
    
    if (!message || !message.query_id) {
      console.warn("Message or query_id not found for feedback", { message, messageId });
      return;
    }

    // Update UI immediately for better UX
    const newMessageList = [...selectedSession.messages].map((item) =>
      item.id === messageId ? { ...item, feedback: passedFeedback } : item
    );
    const newSelectedSession = { ...selectedSession, messages: newMessageList };
    setSelectedSession(newSelectedSession);

    // Send feedback to backend (following Arlo pattern)
    try {
      const userId = session.data?.user?.email || 
                    session.data?.user?.id || 
                    session.data?.user?.name || 
                    "dev-user";
      const feedbackData = {
        query_id: message.query_id,
        user_id: userId,
        session_id: selectedSession.id,
        feedback_type: "detailed",
        feedback_text: passedFeedback,
        vote: message.vote || 0, // Include current vote state
        agent_specific_feedback: {} // Can be enhanced later for agent-specific feedback
      };

      const response = await fetch(`${process.env.NEXT_PUBLIC_MEDIA_BACKEND_URL}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          "X-Token": "coneofsilence",
        },
        body: JSON.stringify(feedbackData)
      });

      if (!response.ok) {
        console.error('Failed to submit feedback:', response.status);
        // Optionally revert UI change on failure
      } else {
        const result = await response.json();
        console.log('Feedback submitted:', result.message);
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
      // Optionally revert UI change on failure
    }
  }

  function updateCurrentSessionWithSummary(
    summary: SessionSummaryObject,
    messagesLength?: number
  ): void {
    if (!selectedSession) return;
    summary.isExpectingDisplay = true;
    if (messagesLength) {
      summary.sessionMessageLengthOnLastUpdate = messagesLength;
    }
    setSelectedSession({ ...selectedSession, summary });
  }

  function removeExpectedDisplayFromSelectedSessionSummary(): void {
    if (!selectedSession) return;
    const newSummary = selectedSession.summary;
    if (newSummary) newSummary.isExpectingDisplay = false;
    setSelectedSession({ ...selectedSession, summary: newSummary });
  }

  async function getServerChatbotResponse(
    messageText: string,
    passedSession: SessionObject
  ): Promise<void> {
    const userId = session.data?.user?.id;
    if (!userId) return;
    await handleServerChatbotResponse(userId, messageText, passedSession);
  }

  function handleAgentStatusChange(event: MessageEvent): void {
    if (event.data && typeof event.data === "string") {
      setChatLoadingMessage(getLoadingMessageFromAgentStatus(event.data));
    }
  }

  async function handleServerChatbotResponse(
    userId: string,
    messageText: string,
    passedSession: SessionObject
  ): Promise<void> {
    setIsChatLoading(true);
    const agentEvent = new EventSource(
      `${process.env.NEXT_PUBLIC_BACKEND_URL ?? ""}currentStatus?uid=${userId}&sid=${passedSession.id}`
    );
    try {
      agentEvent.onmessage = handleAgentStatusChange;
      const data = await fetchChatbotResponse(
        userId,
        messageText,
        passedSession.id,
        selectedChatbotV,
        selectedGenAIBot
      );
      updateSessionListWithNewMessage(
        formatMessageFromServerResponse(data),
        passedSession
      );
    } catch (error) {
      // eslint-disable-next-line no-console -- Current handling (consider a different error handling)
      console.error("Error in chatbot response:", error);
    } finally {
      setIsChatLoading(false);
      setChatLoadingMessage(""); // Reset loading message when request completes
      agentEvent.close();
    }
  }

  function getSessionSummary(): void {
    const userId = session.data?.user?.id;
    if (!userId || !selectedSession) return;
    // If we already have the summary and the length of the messages hasn't changed, serve it again.
    if (
      selectedSession.summary?.sessionMessageLengthOnLastUpdate &&
      selectedSession.summary.sessionMessageLengthOnLastUpdate ===
      selectedSession.messages.length
    ) {
      updateCurrentSessionWithSummary(
        selectedSession.summary,
        selectedSession.messages.length
      );
      return;
    }
    void requestSessionSummary(
      userId,
      selectedSession.id,
      selectedSession.messages.length
    );
  }

  async function requestSessionSummary(
    userId: string,
    sessionId: string,
    messagesLength?: number
  ): Promise<void> {
    setIsChatLoading(true);
    try {
      const data = await fetchSessionSummary(userId, sessionId);
      updateCurrentSessionWithSummary(data, messagesLength);
    } catch (error) {
      // eslint-disable-next-line no-console -- Current handling (consider a different error handling)
      console.error("Error in fetching summary response:", error);
    } finally {
      setIsChatLoading(false);
      setChatLoadingMessage(""); // Reset loading message when request completes
    }
  }

  function formatMessageFromServerResponse(
    data: ChatMessageResponse,
    queryId?: string
  ): ChatMessageObject {
    const usedSession = selectedSession ?? sessions[0];
    // Find highest id of non-bot messages
    const botIdNumbersList = usedSession.messages
      .filter((item) => item.isBot)
      .map((botItem) =>
        Number(botItem.id.slice(CHATBOT_MESSAGE_ID_PREFIX.length))
      );
    const newId =
      CHATBOT_MESSAGE_ID_PREFIX +
      (botIdNumbersList.length > 0
        ? Math.max(...botIdNumbersList) + 1
        : 0
      ).toString();
    const newMessage: ChatMessageObject = {
      id: newId,
      date: new Date().toISOString(),
      isBot: true,
      text: data.text,
      relatedQueries: data.relatedQueries,
      userName: "elevaite",
      query_id: queryId, // Add the query_id to the bot message
      files: data.refs.map((item) => {
        return {
          id: item + new Date().toISOString(),
          filename: item,
        };
      }),
    };
    console.log("Bot message with query_id:", queryId, newMessage); // Debug log
    return newMessage;
  }

  async function addNewBotMessage(messageText: string): Promise<void> {
    if (!messageText || !selectedSession) {
      console.error("No session selected or empty message");
      return;
    }
    try {
      const botMessages = selectedSession.messages.filter(msg => msg.isBot);
      const lastBotId = botMessages.length > 0
        ? Math.max(...botMessages.map(msg =>
            Number(msg.id.replace(CHATBOT_MESSAGE_ID_PREFIX, "")))
          )
        : -1;
      const newId = `${CHATBOT_MESSAGE_ID_PREFIX}${lastBotId + 1}`;
      const newMessage: ChatMessageObject = {
        id: newId,
        date: new Date().toISOString(),
        isBot: true,
        text: messageText,
        userName: "elevaite",
        relatedQueries: [],
      };
      const updatedSession = updateSessionListWithNewMessage(newMessage, selectedSession);
      setSelectedSession(updatedSession);
    } catch (error) {
      console.error("Failed to add bot message:", error);
      // Consider adding error state handling
    }
  }

  async function addNewUserMessageWithLastMessages(messageText: string, file?: File): Promise<void> {
    const MAX_PAYLOAD_HISTORY = 3;
    if (!messageText || !selectedSession) return;

    function fileToBase64(file: File): Promise<string | ArrayBuffer | null> {
      return new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.readAsDataURL(file);
          reader.onload = () => {resolve(reader.result)};
          reader.onerror = error => reject(error);
      });
    }
    let imageBase64: string | ArrayBuffer | null = null;
    if (file) {
      imageBase64 = await fileToBase64(file);
      // console.log(imageBase64);
    }

    const userIdNumbersList = selectedSession.messages
        .filter((item) => !item.isBot)
        .map((userItem) =>
            Number(userItem.id.slice(USER_MESSAGE_ID_PREFIX.length))
        );

    const newId = USER_MESSAGE_ID_PREFIX + (userIdNumbersList.length > 0
        ? Math.max(...userIdNumbersList) + 1
        : 0).toString();

    // Generate a unique query ID for this message
    const queryId = generateQueryId();
    console.log("Generated query_id:", queryId); // Debug log

    const newMessage: ChatMessageObject = {
        id: newId,
        date: new Date().toISOString(),
        isBot: false,
        creative: typeof imageBase64 === 'string' ? imageBase64 : undefined,
        userName: session.data?.user?.name ?? "You",
        text: messageText,
        query_id: queryId,
    };

    console.log("User message with query_id:", newMessage); // Debug log

    // Update session with new user message
    const newSession = updateSessionListWithNewMessage(newMessage, selectedSession);

    // Store the queryId for use in bot response
    const currentQueryId = queryId;

    let ConversationPayload: ChatBotPayload[] = [];
    for (let i = 0; i < selectedSession.messages.length; i++) {
        if (i > MAX_PAYLOAD_HISTORY) break;
        const message = selectedSession.messages[selectedSession.messages.length - i - 1];
        ConversationPayload.push(
            { "actor": message.isBot ? "system" : "user", "content": message.text }
        );
    }

    setIsChatLoading(true);
    ConversationPayload = ConversationPayload.reverse();
    // console.log("CONVERSATION_PAYLOAD:", conversation_payload);
    const userId = session.data?.user?.name ?? "dev-user";
    // console.log("USER_ID:",userId,"Session_ID:",selectedSession.id);
    // Fetching with streaming
    const endpoint = `${process.env.NEXT_PUBLIC_MEDIA_BACKEND_URL}`;
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
          'Accept': 'text/event-stream',
          'Content-Type': 'application/json',
          "X-Token": "coneofsilence",
      },
      body: JSON.stringify({
          "conversation_payload": ConversationPayload,
          "query": messageText,
          "query_id": queryId,
          "skip_llm_call": false,
          "creative": imageBase64,
          "user_id": userId,
          "session_id": selectedSession.id
      })
  });
  if (!response.body) {
    console.error("Response body is null.");
    setIsChatLoading(false);
    setChatLoadingMessage(""); // Reset loading message when request fails
    return;
  }
  if (!response.ok) {
    console.error(`HTTP error! status: ${response.status}`);
    setIsChatLoading(false);
    setChatLoadingMessage(""); // Reset loading message when request fails
    return;
  }
  // console.log("RESPONSE:",response);
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = '';
  let fullResponse = '';

// Uncomment for Streaming
//   const TYPING_SPEED = 0.5;
//   function simulateTyping(text) {
//     return new Promise<void>((resolve) => {
//         let index = 0;
//         let currentResponse = '';
//         const typingInterval = setInterval(() => {
//             if (index < text.length) {
//                 currentResponse = text[index];
//                 fullResponse += currentResponse
//                 updateSessionListWithNewMessage(
//                     formatMessageFromServerResponse({ text: fullResponse, refs: [] }),
//                     newSession
//                 );
//                 index++;
//             } else {
//                 clearInterval(typingInterval);
//                 resolve(); // Resolve without arguments once typing is complete
//             }
//         }, TYPING_SPEED); // Adjust typing speed here
//     });
// }

//   while (true) {
//     const { done, value } = await reader.read();
//     if (done) break;

//     buffer += decoder.decode(value, { stream: true });
//     const lines = buffer.split('\n\n');
//     buffer = lines.pop() || '';

//     for (const line of lines) {
//         if (line.startsWith('data: ')) {
//             try {
//                 const jsonStr = line.slice(6); // Remove 'data: ' prefix
//                 const json = JSON.parse(jsonStr);
//                 console.log("Parsed JSON:", json.response);
//                 const responseText = json.response;
//                 // Simulate typing for each new chunk of response
//                 await simulateTyping(responseText);

//             } catch (e) {
//                 console.error("Error parsing JSON:", e);
//             }
//         }
//     }
// }
// setIsChatLoading(false);
// }
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
        if (line.startsWith('data: ')) {
            try {
                console.log("LINE:",line);
                const jsonStr = line.slice(6); // Remove 'data: ' prefix
                const json = JSON.parse(jsonStr);
                let relatedQueries: string[] = [];

                // Handle image generation status updates
                if (json.status && json.message) {
                    console.log("Image generation status:", json.status, json.message);
                    setChatLoadingMessage(json.message);
                }

                // Handle partial image results for multi-generate
                if (json.status === "partial_result" && json.result && json.result.MarkdownOutput) {
                    console.log("Partial image result:", json.result.MarkdownOutput);
                    // For partial results, we append to the existing response
                    if (json.result.MarkdownOutput) {
                        if (!fullResponse.includes(json.result.MarkdownOutput)) {
                            fullResponse +="\n"+json.result.MarkdownOutput + "\n\n";

                            // Update the message immediately with each new image
                            updateSessionListWithNewMessage(
                                formatMessageFromServerResponse({
                                    text: fullResponse,
                                    refs: [],
                                    relatedQueries: relatedQueries
                                }, currentQueryId),
                                newSession
                            );
                        }
                    }
                }

                // Handle normal response
                if (json.response) {
                    console.log("Parsed JSON:", json.response);
                    const responseText = json.response;

                    // Check if this is a partial response (from multi-generate)
                    if (json.partial === true) {
                        // For partial responses, append to fullResponse if not already included
                        if (!fullResponse.includes(responseText)) {
                            fullResponse += responseText;

                            // Update the message with the new content
                            updateSessionListWithNewMessage(
                                formatMessageFromServerResponse({
                                    text: fullResponse,
                                    refs: [],
                                    relatedQueries: relatedQueries
                                }, currentQueryId),
                                newSession
                            );
                        }
                    } else {
                        // For non-partial responses, append to fullResponse
                        fullResponse += responseText;

                        // Update the message with the new content
                        updateSessionListWithNewMessage(
                            formatMessageFromServerResponse({
                                text: fullResponse,
                                refs: [],
                                relatedQueries: relatedQueries
                            }, currentQueryId),
                            newSession
                        );
                    }
                }

                // Handle related queries
                if (json.related_queries) {
                    relatedQueries = json.related_queries;

                    // Update the message with related queries
                    updateSessionListWithNewMessage(
                        formatMessageFromServerResponse({ text: fullResponse, refs: [], relatedQueries: relatedQueries}, currentQueryId),
                        newSession
                    );
                }
            } catch (e) {
                console.error("Error parsing JSON:", e);
            }
        }
    }
}
setIsChatLoading(false);
setChatLoadingMessage(""); // Reset loading message when request completes
}

  // Simple insertion order loading state management
  function setInsertionOrderLoading(loading: boolean, message?: string): void {
    setIsChatLoading(loading);
    setChatLoadingMessage(loading ? (message || "Creating insertion order...") : "");
  }



  // Debug log to see when context value changes
  console.log(`[CONTEXT_PROVIDER] Rendering with selectedSession messages count: ${selectedSession?.messages?.length || 0}`);

  return (
    <ChatContext.Provider
      value={{
        sessions,
        addNewSession,
        deleteSessionById,
        clearAllSessions,
        selectedSession,
        setSelectedSession: setInternallySelectedSession,
        selectedGenAIBot,
        setSelectedGenAIBot,
        isChatLoading,
        chatLoadingMessage,
        isSessionLoading,
        addNewUserMessageToCurrentSession,
        updateMessageVote,
        updateMessageFeedback,
        getSessionSummary,
        removeExpectedDisplayFromSelectedSessionSummary,
        addNewUserMessageWithLastMessages,
        addNewBotMessage,
        loadUserSessions,
        loadSessionDetails,
        setInsertionOrderLoading,
      }}
    >
      {props.children}
    </ChatContext.Provider>
  );
}

export function useChat(): ChatContextStructure {
  return useContext(ChatContext);
}
