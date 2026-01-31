"use client"

import * as React from "react"
import { X } from "lucide-react"
import { Input } from "./input"
import { Button } from "./button"
import { cn } from "@/lib/utils"

interface TagInputProps {
  placeholder?: string
  tags: string[]
  setTags: (tags: string[]) => void
  maxTags?: number
  maxLength?: number
  className?: string
}

export function TagInput({
  placeholder,
  tags,
  setTags,
  maxTags = 10,
  maxLength = 50,
  className,
}: TagInputProps) {
  const [inputValue, setInputValue] = React.useState("")

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault()
      addTag()
    } else if (e.key === "Backspace" && !inputValue && tags.length > 0) {
      removeTag(tags.length - 1)
    }
  }

  const addTag = () => {
    const trimmed = inputValue.trim()
    if (!trimmed) return

    if (trimmed.length > maxLength) {
      // Could show toast error here
      return
    }

    if (tags.length >= maxTags) {
      // Could show toast error here
      return
    }

    if (!tags.includes(trimmed)) {
      setTags([...tags, trimmed])
    }
    setInputValue("")
  }

  const removeTag = (index: number) => {
    setTags(tags.filter((_, i) => i !== index))
  }

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag, index) => (
          <span
            key={index}
            className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-1 text-sm font-medium text-slate-900"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(index)}
              className="text-slate-500 hover:text-slate-900"
            >
              <X className="h-3 w-3" />
              <span className="sr-only">Remove {tag}</span>
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <Input
          type="text"
          placeholder={placeholder}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={maxLength}
          disabled={tags.length >= maxTags}
        />
        <Button 
          type="button" 
          onClick={addTag}
          disabled={!inputValue.trim() || tags.length >= maxTags}
          variant="outline"
        >
          Add
        </Button>
      </div>
      <div className="text-xs text-slate-500">
        {tags.length}/{maxTags} tags. Press Enter to add.
      </div>
    </div>
  )
}
