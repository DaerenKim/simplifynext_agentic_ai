import { useState, useEffect, useCallback } from 'react';

interface BurnoutState {
  score: number;
  lastEval: string | null;
  questionsCompleted: string[];
  nextQuestionDue: string | null;
}

export const useBurnoutTimer = () => {
  const [burnoutState, setBurnoutState] = useState<BurnoutState>({
    score: 35, // Default 35%
    lastEval: null,
    questionsCompleted: [],
    nextQuestionDue: null
  });

  const [questionsAvailable, setQuestionsAvailable] = useState(false);

  // Check if initial questions need to be completed
  const needsInitialQuestions = burnoutState.questionsCompleted.length < 5;

  // Calculate next interval based on burnout score
  const calculateNextInterval = useCallback((score: number): number => {
    const MIN_INTERVAL_MIN = 30;
    const MAX_INTERVAL_MIN = 4 * 60; // 4 hours
    const LOGISTIC_STEEPNESS = 4.0;
    
    const ratio = 1.0 / (1.0 + Math.exp(-LOGISTIC_STEEPNESS * (score / 100 - 0.5)));
    const minutes = MIN_INTERVAL_MIN + (MAX_INTERVAL_MIN - MIN_INTERVAL_MIN) * (1.0 - ratio);
    return Math.round(minutes);
  }, []);

  // Update burnout state after completing questions
  const updateBurnoutState = useCallback((newScore: number, questionIds: string[]) => {
    const now = new Date().toISOString();
    const intervalMinutes = calculateNextInterval(newScore);
    const nextDue = new Date(Date.now() + intervalMinutes * 60 * 1000).toISOString();

    setBurnoutState(prev => ({
      score: newScore,
      lastEval: now,
      questionsCompleted: [...prev.questionsCompleted, ...questionIds],
      nextQuestionDue: nextDue
    }));

    setQuestionsAvailable(false);

    // Store in localStorage for persistence
    localStorage.setItem('burnoutState', JSON.stringify({
      score: newScore,
      lastEval: now,
      questionsCompleted: [...burnoutState.questionsCompleted, ...questionIds],
      nextQuestionDue: nextDue
    }));
  }, [calculateNextInterval, burnoutState.questionsCompleted]);

  // Load state from localStorage on mount
  useEffect(() => {
    // Clear localStorage for testing - remove this line for production
    localStorage.removeItem('burnoutState');
    
    const saved = localStorage.getItem('burnoutState');
    if (saved) {
      try {
        const parsedState = JSON.parse(saved);
        setBurnoutState(parsedState);
      } catch (error) {
        console.error('Failed to parse saved burnout state:', error);
      }
    }
  }, []);

  // Check if new questions are due
  useEffect(() => {
    if (burnoutState.nextQuestionDue && !needsInitialQuestions) {
      const checkInterval = setInterval(() => {
        const now = new Date();
        const dueTime = new Date(burnoutState.nextQuestionDue!);
        
        if (now >= dueTime) {
          setQuestionsAvailable(true);
        }
      }, 60000); // Check every minute

      return () => clearInterval(checkInterval);
    }
  }, [burnoutState.nextQuestionDue, needsInitialQuestions]);

  return {
    burnoutState,
    questionsAvailable: questionsAvailable || needsInitialQuestions,
    needsInitialQuestions,
    updateBurnoutState
  };
};