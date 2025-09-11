import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { X } from "lucide-react";

interface BurnoutQuestionnaireProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: (score: number, answers: Record<string, number>) => void;
  questions: Array<{
    id: string;
    text: string;
    scale: number;
  }>;
}

export const BurnoutQuestionnaire = ({ 
  isOpen, 
  onClose, 
  onComplete, 
  questions 
}: BurnoutQuestionnaireProps) => {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});

  if (!isOpen || !questions.length) return null;

  const handleAnswer = (value: number) => {
    const currentQ = questions[currentQuestion];
    const newAnswers = { ...answers, [currentQ.id]: value };
    setAnswers(newAnswers);

    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else {
      // Calculate basic score (average)
      const totalScore = Object.values(newAnswers).reduce((sum, val) => sum + val, 0);
      const averageScore = totalScore / questions.length;
      const percentage = ((averageScore - 1) / (5 - 1)) * 100; // Convert 1-5 scale to 0-100%
      
      onComplete(percentage, newAnswers);
      
      // Reset for next time
      setCurrentQuestion(0);
      setAnswers({});
    }
  };

  const question = questions[currentQuestion];
  const progress = ((currentQuestion + 1) / questions.length) * 100;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-2xl shadow-glow">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-xl font-medium">Burnout Assessment</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Question {currentQuestion + 1} of {questions.length}
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
              {question.text}
            </h3>

            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((value) => (
                <Button
                  key={value}
                  variant="outline"
                  className="w-full p-4 text-left justify-start hover:bg-primary-soft transition-gentle"
                  onClick={() => handleAnswer(value)}
                >
                  {value} - {value === 1 ? "Strongly Disagree" : 
                           value === 2 ? "Disagree" :
                           value === 3 ? "Neutral" :
                           value === 4 ? "Agree" : "Strongly Agree"}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};