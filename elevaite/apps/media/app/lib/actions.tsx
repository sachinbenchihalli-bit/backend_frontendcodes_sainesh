"use server";
import { redirect } from "next/navigation";
import { isChatMessageResponse, isSessionSummaryResponse } from "./discriminators";
import type { ChatBotGenAI, ChatMessageResponse, ChatbotV, SessionSummaryObject, ChatBotPayload } from "./interfaces";



const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL;



// eslint-disable-next-line @typescript-eslint/require-await -- Server actions must be async functions
export async function logOut(): Promise<void> {
  redirect(`${process.env.NEXTAUTH_URL_INTERNAL ?? ""}/api/signout`);
}



export async function fetchChatbotResponse(userId: string, messageText: string, sessionId: string, chatbotV: ChatbotV, chatbotGenAi: ChatBotGenAI): Promise<ChatMessageResponse> {
  const url = new URL(`${BACKEND_URL ?? ""}${chatbotV}?query=${messageText}&uid=${userId}&sid=${sessionId}&collection=${chatbotGenAi}`);
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to fetch");
  const data: unknown = await response.json();
  if (isChatMessageResponse(data)) return data;
  throw new Error("Invalid data type");
}



export async function fetchSessionSummary(userId: string, sessionId: string): Promise<SessionSummaryObject> {
  const url = new URL(`${BACKEND_URL ?? ""}summarization?uid=${userId}&sid=${sessionId}`);
  const response = await fetch(url);
  if (!response.ok) throw new Error("Failed to fetch");
  const data: unknown = await response.json();
  if (isSessionSummaryResponse(data)) return data;
  throw new Error("Invalid data type");
}

export async function createInsertionOrder(formData: any): Promise<{
  file_details: { pdf_web_view_link: string };
  sheet_id: string;
  campaign_folder_id: string;
}> {
  const response = await fetch(`${process.env.NEXT_PUBLIC_MEDIA_BACKEND_URL}/create-insertion-order`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(formData)
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error('Failed to create insertion order:', errorText);
    throw new Error(`Failed to submit form: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function sendChatMessage(messageText: string, conversation_payload: ChatBotPayload[]) {
  const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL ?? ""}/`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      "X-Token": "coneofsilence",
    },
    body: JSON.stringify({
      conversation_payload: conversation_payload,
      query: messageText,
      skip_llm_call: false,
      use_openai_directly: true,
    }),
  });

  return response.json();
}

