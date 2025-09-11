import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

interface OnboardingData {
  name: string;
  age: string;
  peaceActivities: string[];
  freeDayActivities: string[];
  goals: string[];
}

interface OnboardingFlowProps {
  onComplete: (data: OnboardingData) => void;
}

const peaceOptions = [
  "Sleep", "Meditation", "Exercise", "Eating", "Reading", 
  "Nature walks", "Music", "Journaling", "Deep breathing"
];

const freeDayOptions = [
  "Exercise", "Sleep all day", "Eat", "Meditate", "Travel", 
  "Spend time with friends", "Read", "Watch movies", "Create art"
];

const goalOptions = [
  "Stress less", "Learn to say no to overworking", "Manage anxiety", 
  "Talk to someone about your burnout", "Manage my time", 
  "Improve work-life balance", "Build healthy habits"
];

export const OnboardingFlow = ({ onComplete }: OnboardingFlowProps) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [data, setData] = useState<OnboardingData>({
    name: "",
    age: "",
    peaceActivities: [],
    freeDayActivities: [],
    goals: []
  });

  const questions = [
    {
      title: "What would you like us to call you?",
      type: "text"
    },
    {
      title: "What is your age?",
      type: "select"
    },
    {
      title: "What puts your mind at peace?",
      type: "multiselect",
      options: peaceOptions,
      field: "peaceActivities"
    },
    {
      title: "If you had one free day today, what would you do?",
      type: "multiselect", 
      options: freeDayOptions,
      field: "freeDayActivities"
    },
    {
      title: "Lastly, what is your unfrazzle goal?",
      type: "multiselect",
      options: goalOptions,
      field: "goals"
    }
  ];

  const handleNext = () => {
    if (currentStep < questions.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onComplete(data);
    }
  };

  const handleMultiSelect = (field: string, value: string) => {
    setData(prev => ({
      ...prev,
      [field]: prev[field as keyof OnboardingData].includes(value) 
        ? (prev[field as keyof OnboardingData] as string[]).filter(item => item !== value)
        : [...(prev[field as keyof OnboardingData] as string[]), value]
    }));
  };

  const isStepValid = () => {
    const question = questions[currentStep];
    if (question.type === "text") return data.name.length > 0;
    if (question.type === "select") return data.age.length > 0;
    if (question.type === "multiselect") {
      const field = question.field as keyof OnboardingData;
      return (data[field] as string[]).length > 0;
    }
    return false;
  };

  const currentQuestion = questions[currentStep];

  return (
    <div className="min-h-screen bg-gradient-subtle flex items-center justify-center p-6">
      <Card className="w-full max-w-2xl shadow-soft">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-light text-foreground">
            {currentQuestion.title}
          </CardTitle>
          <div className="flex justify-center mt-4">
            {questions.map((_, index) => (
              <div
                key={index}
                className={`w-3 h-3 rounded-full mx-1 transition-gentle ${
                  index <= currentStep ? 'bg-primary' : 'bg-muted'
                }`}
              />
            ))}
          </div>
        </CardHeader>

        <CardContent className="space-y-6">
          {currentQuestion.type === "text" && (
            <Input
              placeholder="Enter your name"
              value={data.name}
              onChange={(e) => setData(prev => ({ ...prev, name: e.target.value }))}
              className="text-lg p-4"
            />
          )}

          {currentQuestion.type === "select" && (
            <Select value={data.age} onValueChange={(value) => setData(prev => ({ ...prev, age: value }))}>
              <SelectTrigger className="text-lg p-4">
                <SelectValue placeholder="Select your age range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="18-25">18-25</SelectItem>
                <SelectItem value="26-35">26-35</SelectItem>
                <SelectItem value="36-45">36-45</SelectItem>
                <SelectItem value="46-55">46-55</SelectItem>
                <SelectItem value="56+">56+</SelectItem>
              </SelectContent>
            </Select>
          )}

          {currentQuestion.type === "multiselect" && currentQuestion.options && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {currentQuestion.options.map((option) => {
                const field = currentQuestion.field as keyof OnboardingData;
                const isSelected = (data[field] as string[]).includes(option);
                return (
                  <Badge
                    key={option}
                    variant={isSelected ? "default" : "outline"}
                    className={`p-3 cursor-pointer text-center justify-center transition-gentle hover:scale-105 ${
                      isSelected ? 'bg-primary text-primary-foreground' : 'hover:bg-primary-soft'
                    }`}
                    onClick={() => handleMultiSelect(currentQuestion.field!, option)}
                  >
                    {option}
                  </Badge>
                );
              })}
            </div>
          )}

          <div className="flex justify-between pt-6">
            <Button
              variant="outline"
              onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
              disabled={currentStep === 0}
            >
              Previous
            </Button>

            <Button
              onClick={handleNext}
              disabled={!isStepValid()}
              className="px-8"
            >
              {currentStep === questions.length - 1 ? "Complete" : "Next"}
            </Button>
          </div>

          {currentStep === questions.length - 1 && (
            <p className="text-center text-muted-foreground text-sm mt-4">
              Don't worry if you have multiple unfrazzle goals, because unfrazzle can help you solve them
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};