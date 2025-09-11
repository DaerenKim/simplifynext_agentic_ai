import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";

interface QuestionnaireModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: (score: number) => void;
}

const burnoutQuestions = [
  {
    question: "How often do you feel emotionally drained by your work?",
    options: ["Never", "Rarely", "Sometimes", "Often", "Always"],
    weights: [0, 1, 2, 3, 4]
  },
  {
    question: "Do you feel overwhelmed by your workload?",
    options: ["Never", "Rarely", "Sometimes", "Often", "Always"],
    weights: [0, 1, 2, 3, 4]
  },
  {
    question: "How difficult is it for you to relax after work?",
    options: ["Very easy", "Easy", "Moderate", "Difficult", "Very difficult"],
    weights: [0, 1, 2, 3, 4]
  },
  {
    question: "Do you feel a sense of accomplishment from your work?",
    options: ["Always", "Often", "Sometimes", "Rarely", "Never"],
    weights: [0, 1, 2, 3, 4]
  },
  {
    question: "How often do you dread going to work?",
    options: ["Never", "Rarely", "Sometimes", "Often", "Always"],
    weights: [0, 1, 2, 3, 4]
  }
];

export const QuestionnaireModal = ({ isOpen, onClose, onComplete }: QuestionnaireModalProps) => {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);

  if (!isOpen) return null;

  const handleAnswer = (answerIndex: number) => {
    const newAnswers = [...answers];
    newAnswers[currentQuestion] = burnoutQuestions[currentQuestion].weights[answerIndex];
    setAnswers(newAnswers);

    if (currentQuestion < burnoutQuestions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else {
      // Calculate final score
      const totalScore = newAnswers.reduce((sum, score) => sum + score, 0);
      const maxPossibleScore = burnoutQuestions.length * 4;
      const burnoutPercentage = (totalScore / maxPossibleScore) * 100;
      
      onComplete(burnoutPercentage);
      
      // Reset for next time
      setCurrentQuestion(0);
      setAnswers([]);
    }
  };

  const question = burnoutQuestions[currentQuestion];
  const progress = ((currentQuestion + 1) / burnoutQuestions.length) * 100;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl shadow-glow">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-xl font-medium">Burnout Assessment</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Question {currentQuestion + 1} of {burnoutQuestions.length}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Progress bar */}
          <div className="w-full bg-muted rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Question */}
          <div className="text-center">
            <h3 className="text-lg font-medium text-foreground mb-6">
              {question.question}
            </h3>

            <div className="space-y-3">
              {question.options.map((option, index) => (
                <Button
                  key={index}
                  variant="outline"
                  className="w-full p-4 text-left justify-start hover:bg-primary-soft transition-gentle"
                  onClick={() => handleAnswer(index)}
                >
                  {option}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};