import { useEffect } from 'react';

interface QueuedTypingMessageProps {
  id: string;
  message: string;
  onComplete?: () => void;
  addToQueue: (item: { id: string; text: string; speed: number; onComplete?: () => void }) => void;
  getTypingText: (id: string, fallbackText: string) => string;
  isCurrentlyTyping: (id: string) => boolean;
}

export const QueuedTypingMessage = ({ 
  id, 
  message, 
  onComplete, 
  addToQueue, 
  getTypingText, 
  isCurrentlyTyping 
}: QueuedTypingMessageProps) => {
  
  useEffect(() => {
    addToQueue({
      id,
      text: message,
      speed: 15,
      onComplete,
    });
  }, [id, message, onComplete, addToQueue]);

  const displayedText = getTypingText(id, message);
  const showCursor = isCurrentlyTyping(id);

  // If not yet processed or still typing, show the typing state
  if (displayedText === '' && !showCursor) {
    return <span></span>; // Waiting in queue
  }

  return (
    <span>
      {displayedText}
      {showCursor && <span className="animate-pulse">|</span>}
    </span>
  );
};