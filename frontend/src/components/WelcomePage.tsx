import { useState } from "react";
import { Button } from "@/components/ui/button";

interface WelcomePageProps {
  onStart: () => void;
}

export const WelcomePage = ({ onStart }: WelcomePageProps) => {
  const [showContent, setShowContent] = useState(false);

  // Show content after a brief delay for smooth animation
  setTimeout(() => setShowContent(true), 500);

  return (
    <div className="min-h-screen bg-gradient-calm animate-gradient flex items-center justify-center relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-primary/10 rounded-full animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-48 h-48 bg-accent/10 rounded-full animate-float" style={{ animationDelay: '2s' }} />
        <div className="absolute top-1/2 right-1/3 w-32 h-32 bg-secondary/10 rounded-full animate-float" style={{ animationDelay: '4s' }} />
      </div>

      {/* Main content */}
      <div className={`text-center z-10 transition-all duration-1000 ${showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
        <h1 className="text-6xl md:text-7xl font-light text-white mb-6 tracking-wide">
          Welcome to <span className="font-medium text-yellow-300">Unfrazzle</span>
        </h1>
        
        <p className="text-xl md:text-2xl text-white/80 mb-12 max-w-2xl mx-auto font-light leading-relaxed">
          Your mindful companion for overcoming burnout and finding balance
        </p>

        <Button 
          onClick={onStart}
          variant="default"
          size="lg"
          className="px-12 py-6 text-lg font-medium shadow-soft hover:shadow-glow transition-gentle"
        >
          Begin Your Journey
        </Button>
      </div>
    </div>
  );
};