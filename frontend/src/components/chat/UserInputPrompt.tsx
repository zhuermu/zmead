'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { UserInputOption } from '@/hooks/useChat';

export interface UserInputPromptProps {
  type: 'confirmation' | 'selection' | 'input';
  message: string;
  options?: UserInputOption[];
  onRespond: (response: string) => void;
  isLoading?: boolean;
}

export function UserInputPrompt({
  type,
  message,
  options = [],
  onRespond,
  isLoading = false,
}: UserInputPromptProps) {
  const [customInput, setCustomInput] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const handleOptionClick = (option: UserInputOption) => {
    if (option.value === '其他' || option.value === 'other') {
      setShowCustomInput(true);
    } else {
      onRespond(option.value);
    }
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (customInput.trim()) {
      onRespond(customInput.trim());
      setCustomInput('');
      setShowCustomInput(false);
    }
  };

  const handleCancel = () => {
    onRespond('取消');
  };

  // Confirmation type
  if (type === 'confirmation') {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 my-2">
        <p className="text-sm text-gray-700 mb-3">{message}</p>
        <div className="flex gap-2">
          <Button
            onClick={() => onRespond('确认')}
            disabled={isLoading}
            className="flex-1 bg-green-600 hover:bg-green-700"
          >
            ✅ 确认
          </Button>
          <Button
            onClick={handleCancel}
            disabled={isLoading}
            variant="outline"
            className="flex-1"
          >
            ❌ 取消
          </Button>
        </div>
      </div>
    );
  }

  // Selection type
  if (type === 'selection') {
    return (
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 my-2">
        <p className="text-sm text-gray-700 mb-3">{message}</p>
        
        {!showCustomInput ? (
          <div className="space-y-2">
            {/* Preset options */}
            {options.map((option, index) => (
              <Button
                key={index}
                onClick={() => handleOptionClick(option)}
                disabled={isLoading}
                variant="outline"
                className="w-full justify-start text-left flex-col items-start h-auto py-3"
                title={option.description}
              >
                <span className="font-semibold">{index + 1}️⃣ {option.label}</span>
                {option.description && (
                  <span className="text-xs text-gray-500 mt-1">{option.description}</span>
                )}
              </Button>
            ))}
            
            {/* "Other" option */}
            <Button
              onClick={() => setShowCustomInput(true)}
              disabled={isLoading}
              variant="outline"
              className="w-full justify-start text-left"
            >
              ➕ 其他
            </Button>
            
            {/* Cancel option */}
            <Button
              onClick={handleCancel}
              disabled={isLoading}
              variant="outline"
              className="w-full justify-start text-left text-red-600 hover:text-red-700"
            >
              ❌ 取消
            </Button>
          </div>
        ) : (
          <form onSubmit={handleCustomSubmit} className="space-y-2">
            <Input
              type="text"
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder="请输入自定义选项..."
              disabled={isLoading}
              autoFocus
              className="w-full"
            />
            <div className="flex gap-2">
              <Button
                type="submit"
                disabled={isLoading || !customInput.trim()}
                className="flex-1"
              >
                提交
              </Button>
              <Button
                type="button"
                onClick={() => {
                  setShowCustomInput(false);
                  setCustomInput('');
                }}
                disabled={isLoading}
                variant="outline"
                className="flex-1"
              >
                返回
              </Button>
            </div>
          </form>
        )}
      </div>
    );
  }

  // Input type
  if (type === 'input') {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 my-2">
        <p className="text-sm text-gray-700 mb-3">{message}</p>
        <form onSubmit={handleCustomSubmit} className="space-y-2">
          <Input
            type="text"
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
            placeholder="请输入..."
            disabled={isLoading}
            autoFocus
            className="w-full"
          />
          <div className="flex gap-2">
            <Button
              type="submit"
              disabled={isLoading || !customInput.trim()}
              className="flex-1"
            >
              提交
            </Button>
            <Button
              type="button"
              onClick={handleCancel}
              disabled={isLoading}
              variant="outline"
              className="flex-1"
            >
              取消
            </Button>
          </div>
        </form>
      </div>
    );
  }

  return null;
}
