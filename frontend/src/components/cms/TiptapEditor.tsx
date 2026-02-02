'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Image from '@tiptap/extension-image'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

type Props = {
  value: string
  onChange: (html: string) => void
  onUploadImage: (file: File) => Promise<string>
}

export default function TiptapEditor({ value, onChange, onUploadImage }: Props) {
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  const extensions = useMemo(() => [StarterKit, Image.configure({ inline: false })], [])

  const editor = useEditor({
    extensions,
    content: value || '',
    immediatelyRender: false,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
    editorProps: {
      attributes: {
        class:
          'min-h-[240px] rounded-xl border border-slate-200 bg-white p-4 text-slate-900 focus:outline-none prose max-w-none',
      },
    },
  })

  useEffect(() => {
    if (!editor) return
    const current = editor.getHTML()
    if ((value || '') !== current) {
      editor.commands.setContent(value || '', { emitUpdate: false })
    }
  }, [editor, value])

  const insertImage = async (file: File) => {
    if (!editor) return
    setIsUploading(true)
    try {
      const url = await onUploadImage(file)
      editor.chain().focus().setImage({ src: url }).run()
      toast.success('图片已插入')
    } catch (e: any) {
      toast.error(e?.message || '图片上传失败')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => editor?.chain().focus().toggleBold().run()}
          disabled={!editor}
        >
          Bold
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => editor?.chain().focus().toggleItalic().run()}
          disabled={!editor}
        >
          Italic
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => editor?.chain().focus().toggleBulletList().run()}
          disabled={!editor}
        >
          Bullets
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => editor?.chain().focus().toggleOrderedList().run()}
          disabled={!editor}
        >
          Numbered
        </Button>

        <div className="flex-1" />

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) insertImage(file)
            e.target.value = ''
          }}
        />
        <Button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={!editor || isUploading}
        >
          {isUploading ? 'Uploading…' : 'Insert Image'}
        </Button>
      </div>

      <EditorContent editor={editor} />
    </div>
  )
}

