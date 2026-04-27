"use client";

import React from "react";
import { motion } from "framer-motion";
import { ArrowRight, Code2, FileText, BrainCircuit, TerminalSquare } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#050505] text-white selection:bg-indigo-500/30 overflow-hidden font-sans">
      
      {/* Background Gradients */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-0 -left-1/4 w-1/2 h-1/2 bg-indigo-600/20 blur-[120px] rounded-full" />
        <div className="absolute bottom-0 -right-1/4 w-1/2 h-1/2 bg-purple-600/10 blur-[120px] rounded-full" />
      </div>

      {/* Navbar */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-lg shadow-[0_0_20px_rgba(99,102,241,0.4)]">
            A
          </div>
          <span className="font-semibold text-xl tracking-tight">ATS Pro</span>
        </div>
        <div className="flex items-center gap-6 text-sm font-medium text-gray-400">
          <Link href="#features" className="hover:text-white transition-colors">Features</Link>
          <Link href="#how-it-works" className="hover:text-white transition-colors">How it works</Link>
          <Link href="/interview">
            <Button className="bg-white text-black hover:bg-gray-200 rounded-full px-6 transition-all">
              Launch App
            </Button>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 flex flex-col items-center text-center px-4 pt-32 pb-24 max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-sm text-indigo-300 mb-8"
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
          </span>
          Next-Gen AI Career Platform v2.0
        </motion.div>

        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: "easeOut" }}
          className="text-6xl md:text-8xl font-bold tracking-tighter mb-8 leading-[1.1]"
        >
          Master your <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-500">Resume</span><br />
          Ace the <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-500">Interview</span>
        </motion.h1>

        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
          className="text-xl md:text-2xl text-gray-400 max-w-3xl mb-12 font-light leading-relaxed"
        >
          The ultimate platform bridging academia and industry. Deep ATS optimization combined with a FAANG-grade Leetcode Sandbox.
        </motion.p>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
          className="flex flex-col sm:flex-row items-center gap-4"
        >
          <Link href="/interview">
            <Button className="h-14 px-8 text-lg bg-indigo-600 hover:bg-indigo-700 text-white rounded-full shadow-[0_0_40px_rgba(79,70,229,0.4)] transition-all">
              Try Mock Interview
              <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </Link>
          <Button variant="outline" className="h-14 px-8 text-lg border-white/10 text-white hover:bg-white/5 rounded-full transition-all bg-transparent">
            Upload Resume
            <FileText className="ml-2 w-5 h-5" />
          </Button>
        </motion.div>
      </main>

      {/* Bento Grid Features */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 py-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          <motion.div 
            whileHover={{ y: -5 }}
            className="md:col-span-2 bg-[#111111]/80 backdrop-blur-xl border border-white/10 rounded-3xl p-8 flex flex-col justify-between overflow-hidden relative group"
          >
            <div className="absolute top-0 right-0 p-8 opacity-20 group-hover:opacity-40 transition-opacity">
              <TerminalSquare className="w-48 h-48 text-indigo-500" />
            </div>
            <div className="relative z-10">
              <div className="w-12 h-12 rounded-xl bg-indigo-500/20 flex items-center justify-center mb-6 border border-indigo-500/30">
                <Code2 className="text-indigo-400 w-6 h-6" />
              </div>
              <h3 className="text-3xl font-bold mb-4">FAANG Code Sandbox</h3>
              <p className="text-gray-400 text-lg max-w-md">
                Experience a true Leetcode-style IDE. Run algorithms against hidden test cases. Evaluated instantly by our strict AI Judge evaluating Big-O complexity.
              </p>
            </div>
          </motion.div>

          <motion.div 
            whileHover={{ y: -5 }}
            className="bg-[#111111]/80 backdrop-blur-xl border border-white/10 rounded-3xl p-8 flex flex-col justify-between"
          >
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center mb-6 border border-emerald-500/30">
              <BrainCircuit className="text-emerald-400 w-6 h-6" />
            </div>
            <h3 className="text-2xl font-bold mb-4">Deep Research Agents</h3>
            <p className="text-gray-400">
              We scrape real interview patterns for top companies to generate ultra-targeted, non-generic DSA questions.
            </p>
          </motion.div>

        </div>
      </section>
      
    </div>
  );
}
