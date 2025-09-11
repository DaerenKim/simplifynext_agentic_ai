import { useState, useEffect } from 'react';

interface Question {
  qid: string;
  text: string;
}

export const useBackendQuestions = () => {
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchNextQuestion = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/manager/checkin/next');
      const data = await response.json();
      setCurrentQuestion(data);
    } catch (error) {
      console.error('Failed to fetch question:', error);
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async (qid: string, value: number) => {
    try {
      const response = await fetch('/api/manager/checkin/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ qid, value })
      });
      return await response.json();
    } catch (error) {
      console.error('Failed to submit answer:', error);
      throw error;
    }
  };

  useEffect(() => {
    fetchNextQuestion();
  }, []);

  return { 
    currentQuestion, 
    loading, 
    fetchNextQuestion, 
    submitAnswer 
  };
};