"use client"
import { useContext, useState, useRef } from "react";
import { ChatbotInput } from "./components/ChatbotInput";
import { ChatbotWindow } from "./components/ChatbotWindow";
import { ChatContext } from "./ui/contexts/ChatContext";
import "./page.scss";




export default function Chatbot(): JSX.Element {

  const chatContext = useContext(ChatContext);
  const [inputText, setInputText] = useState("");
  const chatbotInputRef = useRef<any>(null);

  function parentHandleQueryClick(query: string): void {
    if (chatContext.isChatLoading) return;
    setInputText(query);
    chatContext.addNewUserMessageWithLastMessages(query);
    setInputText("");
  }

  function parentHandleGenerateIOClick(): void {
    if (chatbotInputRef.current && chatbotInputRef.current.handleGenerateIOClick) {
      chatbotInputRef.current.handleGenerateIOClick();
    }
  }

  // Determine layout based on whether this is a new session that's ready for first message
  const isNewSessionReady = chatContext.selectedSession?.isNewSession &&
                            chatContext.selectedSession?.hasLoadedMessages &&
                            !chatContext.isSessionLoading;

  return (
    <main className="chatbot-main-container">
      <ChatbotWindow onQueryClick={parentHandleQueryClick} onGenerateIOClick={parentHandleGenerateIOClick}/>
      <div className={isNewSessionReady ? "center-layout": "bottom-layout"}>
        <ChatbotInput ref={chatbotInputRef} text={inputText} setText={setInputText} />
      </div>
    </main>
  );
}
