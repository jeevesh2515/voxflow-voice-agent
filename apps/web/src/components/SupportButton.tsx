"use client";

import { useState } from "react";
import { HelpCircle, Mail, MessageSquare, ExternalLink, X } from "lucide-react";
import { openCrispSupport } from "./CrispChat";

export interface SupportButtonProps {
  userEmail?: string;
  userName?: string;
  variant?: "icon" | "button";
}

export default function SupportButton({ userEmail, userName, variant = "button" }: SupportButtonProps) {
  const [modalOpen, setModalOpen] = useState(false);

  const handleOpenChat = () => {
    openCrispSupport(userEmail, userName);
    setModalOpen(false);
  };

  return (
    <>
      {variant === "icon" ? (
        <button
          onClick={() => setModalOpen(true)}
          title="Operator Support"
          className="p-2 text-[#94a3b8] hover:text-[#00ffcc] hover:bg-[#181826] rounded-xl transition-colors cursor-pointer"
        >
          <HelpCircle size={16} />
        </button>
      ) : (
        <button
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-mono font-medium text-[#cbd5e1] hover:text-white bg-[#181826] hover:bg-[#202034] border border-[#28283c] transition-colors cursor-pointer"
        >
          <HelpCircle size={13} className="text-[#00ffcc]" />
          <span>Support</span>
        </button>
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="bg-[#0e0e1a] border border-[#28283c] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 text-left">
            <div className="flex items-center justify-between border-b border-[#202034] pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-[#00ffcc]/10 border border-[#00ffcc]/30 flex items-center justify-center text-[#00ffcc]">
                  <HelpCircle size={16} />
                </div>
                <div>
                  <h3 className="font-headline font-bold text-sm text-white">VoxFlow Support Desk</h3>
                  <p className="text-[11px] font-mono text-[#94a3b8]">UK Operations & Engineering Support</p>
                </div>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="text-[#94a3b8] hover:text-white p-1 rounded-lg hover:bg-white/5 transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-[#cbd5e1] leading-relaxed">
              Need assistance with your voice pipeline, Amazon Connect lines, or billing? Reach our engineering team directly via live chat or email:
            </p>

            <div className="space-y-2.5">
              <button
                onClick={handleOpenChat}
                className="w-full flex items-center justify-between p-3.5 rounded-xl bg-[#141424] hover:bg-[#1a1a2e] border border-[#242438] hover:border-[#00ffcc]/40 transition-all text-left group cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <MessageSquare size={16} className="text-[#00ffcc]" />
                  <div>
                    <div className="text-xs font-bold text-white group-hover:text-[#00ffcc] transition-colors">
                      Live Chat via Crisp
                    </div>
                    <div className="text-[11px] text-[#94a3b8]">Instant response from our on-call operations engineers</div>
                  </div>
                </div>
                <ExternalLink size={14} className="text-[#64748b] group-hover:text-[#00ffcc]" />
              </button>

              <a
                href="mailto:contact@voxflow.cc?subject=Operations%20Support%20Request"
                className="w-full flex items-center justify-between p-3.5 rounded-xl bg-[#141424] hover:bg-[#1a1a2e] border border-[#242438] hover:border-[#ff2d78]/40 transition-all text-left group"
              >
                <div className="flex items-center gap-3">
                  <Mail size={16} className="text-[#ff2d78]" />
                  <div>
                    <div className="text-xs font-bold text-white group-hover:text-[#ff2d78] transition-colors">
                      Email contact@voxflow.cc
                    </div>
                    <div className="text-[11px] text-[#94a3b8]">24/7 SLA escalation desk with ticket tracking</div>
                  </div>
                </div>
                <ExternalLink size={14} className="text-[#64748b] group-hover:text-[#ff2d78]" />
              </a>
            </div>

            <div className="pt-2 text-center text-[11px] font-mono text-[#64748b]">
              AWS eu-west-2 (London) • 24/7 Monitoring
            </div>
          </div>
        </div>
      )}
    </>
  );
}
