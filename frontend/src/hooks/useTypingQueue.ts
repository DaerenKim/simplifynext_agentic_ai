import { useState, useRef, useEffect } from 'react';

interface TypingQueueItem {
  id: string;
  text: string;
  speed: number;
  onComplete?: () => void;
}

interface TypingState {
  currentText: string;
  isTyping: boolean;
  currentId: string | null;
}

export const useTypingQueue = () => {
  const [typingState, setTypingState] = useState<TypingState>({
    currentText: '',
    isTyping: false,
    currentId: null,
  });
  
  const queueRef = useRef<TypingQueueItem[]>([]);
  const indexRef = useRef(0);
  const timeoutRef = useRef<NodeJS.Timeout>();
  const isProcessingRef = useRef(false);
  const completedItemsRef = useRef<Set<string>>(new Set());

  const addToQueue = (item: TypingQueueItem) => {
    queueRef.current.push(item);
    if (!isProcessingRef.current) {
      processQueue();
    }
  };

  const processQueue = () => {
    if (queueRef.current.length === 0) {
      isProcessingRef.current = false;
      return;
    }

    isProcessingRef.current = true;
    const currentItem = queueRef.current.shift()!;
    
    setTypingState({
      currentText: '',
      isTyping: true,
      currentId: currentItem.id,
    });

    indexRef.current = 0;
    typeNextChar(currentItem);
  };

  const typeNextChar = (item: TypingQueueItem) => {
    if (indexRef.current < item.text.length) {
      setTypingState(prev => ({
        ...prev,
        currentText: item.text.slice(0, indexRef.current + 1),
      }));
      indexRef.current++;
      timeoutRef.current = setTimeout(() => typeNextChar(item), item.speed);
    } else {
      // Mark as completed
      completedItemsRef.current.add(item.id);
      setTypingState(prev => ({
        ...prev,
        isTyping: false,
      }));
      item.onComplete?.();
      
      // Process next item in queue after a small delay
      setTimeout(() => {
        processQueue();
      }, 100);
    }
  };

  const getTypingText = (id: string, fallbackText: string) => {
    // If this item is currently being typed
    if (typingState.currentId === id && typingState.isTyping) {
      return typingState.currentText;
    }
    // If this item was completed, show full text
    if (completedItemsRef.current.has(id)) {
      return fallbackText;
    }
    // If this item is currently finished (but not yet marked complete)
    if (typingState.currentId === id && !typingState.isTyping) {
      return fallbackText;
    }
    // Otherwise, waiting in queue or not processed yet
    return '';
  };

  const isCurrentlyTyping = (id: string) => {
    return typingState.currentId === id && typingState.isTyping;
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    addToQueue,
    getTypingText,
    isCurrentlyTyping,
    isQueueEmpty: () => queueRef.current.length === 0 && !isProcessingRef.current,
  };
};