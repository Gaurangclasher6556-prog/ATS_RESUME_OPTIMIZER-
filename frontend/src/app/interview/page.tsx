"use client";

import React, { useState, useRef } from "react";
import Editor from "@monaco-editor/react";
import { Play, CheckCircle, TerminalSquare, RotateCcw, AlertTriangle } from "lucide-react";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function InterviewIDE() {
  const [code, setCode] = useState<string>("def solve(nums, target):\n    # Write your code here\n    pass\n");
  const [terminalOutput, setTerminalOutput] = useState<string>("> Terminal ready.\\n> Waiting for code execution...");
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<any>(null);

  // Placeholder problem data
  const problem = {
    title: "1. Two Sum (Mock Problem)",
    difficulty: "Medium",
    company: "Google",
    description: `Given an array of integers \`nums\` and an integer \`target\`, return indices of the two numbers such that they add up to \`target\`.

You may assume that each input would have exactly one solution, and you may not use the same element twice.
You can return the answer in any order.`,
    example1: `Input: nums = [2,7,11,15], target = 9
Output: [0,1]
Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].`,
    constraints: `2 <= nums.length <= 10^4\n-10^9 <= nums[i] <= 10^9\n-10^9 <= target <= 10^9`
  };

  const handleRunCode = async () => {
    setIsRunning(true);
    setTerminalOutput("> Running test cases...");
    try {
      // In production, this points to your FastAPI backend
      const res = await fetch("http://127.0.0.1:8000/api/run-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: problem.description, code: code }),
      });
      const data = await res.json();
      setTerminalOutput(data.terminal_output || "No output returned.");
    } catch (e: any) {
      setTerminalOutput("> Execution Error: " + e.message);
    }
    setIsRunning(false);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/api/evaluate-answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: problem.description,
          answer: code,
          job_description: "Software Engineer", // This would be dynamic
          pdf_text: "Candidate Resume", // This would be dynamic
        }),
      });
      const data = await res.json();
      setFeedback(data);
    } catch (e: any) {
      alert("Evaluation failed: " + e.message);
    }
    setIsSubmitting(false);
  };

  return (
    <div className="h-screen w-full bg-[#0d1117] text-[#c9d1d9] flex flex-col font-sans overflow-hidden">
      {/* Navbar */}
      <header className="h-14 border-b border-[#30363d] bg-[#161b22] flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-lg">
            A
          </div>
          <span className="font-semibold tracking-tight text-white/90">ATS Career Pro</span>
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-[#238636]/20 text-[#2ea043] border border-[#238636]/50 ml-4">
            {problem.company} Round
          </span>
        </div>
        <div className="flex items-center gap-4">
          <Button 
            onClick={handleRunCode} 
            disabled={isRunning}
            className="bg-[#21262d] hover:bg-[#30363d] text-[#c9d1d9] border border-[#30363d] h-9 transition-colors"
          >
            <Play className="w-4 h-4 mr-2" />
            {isRunning ? "Running..." : "Run Test Cases"}
          </Button>
          <Button 
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="bg-[#238636] hover:bg-[#2ea043] text-white h-9 shadow-md transition-colors"
          >
            <CheckCircle className="w-4 h-4 mr-2" />
            {isSubmitting ? "Evaluating..." : "Submit Answer"}
          </Button>
        </div>
      </header>

      {/* Main Workspace */}
      {/* @ts-expect-error - resizable panels types are missing direction prop occasionally */}
      <ResizablePanelGroup direction="horizontal" className="flex-grow">
        
        {/* Left Pane: Problem Description */}
        <ResizablePanel defaultSize={40} minSize={30} className="border-r border-[#30363d] bg-[#0d1117]">
          <Tabs defaultValue="description" className="h-full flex flex-col">
            <div className="h-12 border-b border-[#30363d] bg-[#161b22] flex items-center px-4 shrink-0">
              <TabsList className="bg-transparent gap-6">
                <TabsTrigger 
                  value="description" 
                  className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:text-white data-[state=active]:border-b-2 data-[state=active]:border-indigo-500 rounded-none px-0 text-sm"
                >
                  Description
                </TabsTrigger>
                <TabsTrigger 
                  value="solutions" 
                  className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:text-white data-[state=active]:border-b-2 data-[state=active]:border-indigo-500 rounded-none px-0 text-sm"
                >
                  AI Hint
                </TabsTrigger>
              </TabsList>
            </div>
            
            <TabsContent value="description" className="flex-grow p-6 overflow-y-auto m-0">
              <h1 className="text-2xl font-bold text-white mb-4">{problem.title}</h1>
              <div className="flex gap-2 mb-6">
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#d29922]/20 text-[#d29922]">
                  {problem.difficulty}
                </span>
              </div>
              
              <div className="prose prose-invert prose-p:text-[#c9d1d9] prose-p:leading-relaxed max-w-none">
                <p className="whitespace-pre-wrap mb-6">{problem.description}</p>
                
                <h3 className="text-white font-semibold mt-8 mb-3">Example 1:</h3>
                <pre className="bg-[#161b22] border border-[#30363d] rounded-lg p-4 font-mono text-sm overflow-x-auto text-[#e6edf3]">
                  {problem.example1}
                </pre>

                <h3 className="text-white font-semibold mt-8 mb-3">Constraints:</h3>
                <ul className="list-disc pl-5 space-y-2 font-mono text-sm bg-[#161b22] border border-[#30363d] rounded-lg p-4 text-[#e6edf3]">
                  {problem.constraints.split("\\n").map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            </TabsContent>
          </Tabs>
        </ResizablePanel>

        <ResizableHandle withHandle className="bg-[#30363d]" />

        {/* Right Pane: Code Editor + Terminal */}
        <ResizablePanel defaultSize={60} minSize={40}>
          {/* @ts-expect-error */}
          <ResizablePanelGroup direction="vertical">
            
            {/* Editor */}
            <ResizablePanel defaultSize={70} className="relative bg-[#0d1117]">
              <div className="h-10 border-b border-[#30363d] bg-[#161b22] flex items-center px-4 shrink-0 text-xs text-[#8b949e]">
                Python 3
              </div>
              <div className="absolute inset-0 top-10">
                <Editor
                  height="100%"
                  defaultLanguage="python"
                  theme="vs-dark"
                  value={code}
                  onChange={(val) => setCode(val || "")}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                    padding: { top: 16 },
                    scrollBeyondLastLine: false,
                    lineHeight: 1.6,
                  }}
                />
              </div>
            </ResizablePanel>

            <ResizableHandle withHandle className="bg-[#30363d]" />

            {/* Terminal */}
            <ResizablePanel defaultSize={30} minSize={20} className="bg-[#161b22] flex flex-col">
              <div className="h-10 border-b border-[#30363d] bg-[#0d1117] flex items-center px-4 shrink-0 text-xs font-semibold text-[#8b949e] tracking-wide uppercase">
                <TerminalSquare className="w-3.5 h-3.5 mr-2 inline" />
                Testcase Console
              </div>
              <div className="flex-grow p-4 overflow-y-auto font-mono text-sm whitespace-pre-wrap">
                {isRunning ? (
                  <div className="flex items-center text-indigo-400 animate-pulse">
                    <RotateCcw className="w-4 h-4 mr-2 animate-spin" />
                    Executing against hidden test cases...
                  </div>
                ) : (
                  <div className={terminalOutput.includes("Error") ? "text-red-400" : "text-[#a5d6ff]"}>
                    {terminalOutput}
                  </div>
                )}
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>
      </ResizablePanelGroup>

      {/* AI Feedback Dialog */}
      <Dialog open={!!feedback} onOpenChange={() => setFeedback(null)}>
        <DialogContent className="bg-[#0d1117] border-[#30363d] text-[#c9d1d9] max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-white mb-2">
              AI Evaluation Score: <span className={feedback?.score >= 7 ? "text-[#2ea043]" : "text-[#d29922]"}>{feedback?.score}/10</span>
            </DialogTitle>
            <DialogDescription className="text-lg font-medium">
              Grade: {feedback?.grade}
            </DialogDescription>
          </DialogHeader>
          
          <div className="mt-4 space-y-6 max-h-[60vh] overflow-y-auto pr-2">
            <div>
              <h4 className="text-[#2ea043] font-semibold mb-2 flex items-center"><CheckCircle className="w-4 h-4 mr-2"/> Strengths</h4>
              <ul className="list-disc pl-5 space-y-1">
                {feedback?.strengths?.map((s: string, i: number) => <li key={i}>{s}</li>)}
              </ul>
            </div>
            
            <div>
              <h4 className="text-[#f85149] font-semibold mb-2 flex items-center"><AlertTriangle className="w-4 h-4 mr-2"/> Areas to Improve</h4>
              <ul className="list-disc pl-5 space-y-1">
                {feedback?.improvements?.map((s: string, i: number) => <li key={i}>{s}</li>)}
              </ul>
            </div>

            <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
              <h4 className="text-indigo-400 font-semibold mb-2">💡 Ideal Solution</h4>
              <p className="text-sm italic">{feedback?.ideal_answer}</p>
            </div>
            
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
              <h4 className="text-blue-400 font-semibold mb-1">Top Tip</h4>
              <p className="text-sm">{feedback?.tip}</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
