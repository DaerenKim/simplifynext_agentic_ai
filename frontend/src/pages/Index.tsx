import { useState } from "react";
import { WelcomePage } from "@/components/WelcomePage";
import { OnboardingFlow } from "@/components/OnboardingFlow";
import { MainApp } from "@/components/MainApp";

interface OnboardingData {
  name: string;
  age: string;
  peaceActivities: string[];
  freeDayActivities: string[];
  goals: string[];
}

type AppState = "welcome" | "onboarding" | "main";

const Index = () => {
  const [appState, setAppState] = useState<AppState>("welcome");
  const [userData, setUserData] = useState<OnboardingData | null>(null);

  const handleWelcomeComplete = () => {
    setAppState("onboarding");
  };

  const handleOnboardingComplete = (data: OnboardingData) => {
    setUserData(data);
    setAppState("main");
  };

  if (appState === "welcome") {
    return <WelcomePage onStart={handleWelcomeComplete} />;
  }

  if (appState === "onboarding") {
    return <OnboardingFlow onComplete={handleOnboardingComplete} />;
  }

  if (appState === "main" && userData) {
    return <MainApp userData={userData} />;
  }

  return null;
};

export default Index;
