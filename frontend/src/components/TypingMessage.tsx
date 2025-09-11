import { useTypingEffect } from "@/hooks/useTypingEffect";

interface TypingMessageProps {
  message: string;
  onComplete?: () => void;
}

export const TypingMessage = ({ message, onComplete }: TypingMessageProps) => {
  const { displayedText } = useTypingEffect({ 
    text: message, 
    speed: 15,
    onComplete 
  });

  return (
    <span>
      {displayedText}
      <span className="animate-pulse">|</span>
    </span>
  );
};