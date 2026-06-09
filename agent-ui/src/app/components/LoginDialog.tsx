"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

interface LoginDialogProps {
  open: boolean;
  onLogin: (userId: string) => void;
}

export function LoginDialog({ open, onLogin }: LoginDialogProps) {
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = () => {
    const trimmed = username.trim();
    if (!trimmed) {
      setError("请输入用户名");
      return;
    }
    if (trimmed.length > 32) {
      setError("用户名不能超过 32 个字符");
      return;
    }
    if (!/^[a-zA-Z0-9一-鿿_-]+$/.test(trimmed)) {
      setError("用户名只能包含字母、数字、中文、下划线和短横线");
      return;
    }
    setError("");
    onLogin(trimmed);
  };

  return (
    <Dialog open={open}>
      <DialogContent
        className="sm:max-w-[400px]"
        showCloseButton={false}
        onPointerDownOutside={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>欢迎使用个性化教育 Agent</DialogTitle>
          <DialogDescription>
            请输入你的用户名，系统会根据用户名隔离你的对话和记忆。
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <Input
            placeholder="请输入用户名（如 student_a）"
            value={username}
            onChange={(e) => {
              setUsername(e.target.value);
              setError("");
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSubmit();
            }}
            autoFocus
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button onClick={handleSubmit} className="w-full">
            进入系统
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
