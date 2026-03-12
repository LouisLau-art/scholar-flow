'use client'

import { useEffect, useMemo } from 'react'
import Link from '@tiptap/extension-link'
import Underline from '@tiptap/extension-underline'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Bold, Italic, Link2, List, ListOrdered, Underline as UnderlineIcon, Unlink } from 'lucide-react'

import { Button } from '@/components/ui/button'

type ReviewerEmailComposeEditorProps = {
  value: string
  disabled?: boolean
  onChange: (value: string) => void
}

export function ReviewerEmailComposeEditor(props: ReviewerEmailComposeEditorProps) {
  const { value, disabled = false, onChange } = props

  const extensions = useMemo(
    () => [
      StarterKit,
      Underline,
      Link.configure({
        autolink: true,
        openOnClick: false,
        protocols: ['http', 'https', 'mailto'],
      }),
    ],
    []
  )

  const editor = useEditor({
    extensions,
    content: value || '',
    immediatelyRender: false,
    editable: !disabled,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML())
    },
    editorProps: {
      attributes: {
        class:
          'ProseMirror min-h-[320px] rounded-xl border border-border bg-background p-4 text-foreground focus:outline-none prose max-w-none',
      },
    },
  })

  useEffect(() => {
    if (!editor) return
    editor.setEditable(!disabled)
  }, [disabled, editor])

  useEffect(() => {
    if (!editor) return
    const current = editor.getHTML()
    if ((value || '') !== current) {
      editor.commands.setContent(value || '', { emitUpdate: false })
    }
  }, [editor, value])

  const setLink = () => {
    if (!editor || disabled) return
    const currentHref = editor.getAttributes('link').href as string | undefined
    const nextHref = window.prompt('Link URL', currentHref || 'https://')
    if (nextHref === null) return
    const normalized = nextHref.trim()
    if (!normalized) {
      editor.chain().focus().unsetLink().run()
      return
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: normalized }).run()
  }

  const toolbarButtonClass = 'h-8 gap-1.5 px-2 text-xs'

  return (
    <div className="space-y-3" data-testid="reviewer-email-compose-shell">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant={editor?.isActive('bold') ? 'default' : 'outline'}
          className={toolbarButtonClass}
          onClick={() => editor?.chain().focus().toggleBold().run()}
          disabled={!editor || disabled}
        >
          <Bold className="h-3.5 w-3.5" />
          Bold
        </Button>
        <Button
          type="button"
          size="sm"
          variant={editor?.isActive('italic') ? 'default' : 'outline'}
          className={toolbarButtonClass}
          onClick={() => editor?.chain().focus().toggleItalic().run()}
          disabled={!editor || disabled}
        >
          <Italic className="h-3.5 w-3.5" />
          Italic
        </Button>
        <Button
          type="button"
          size="sm"
          variant={editor?.isActive('underline') ? 'default' : 'outline'}
          className={toolbarButtonClass}
          onClick={() => editor?.chain().focus().toggleUnderline().run()}
          disabled={!editor || disabled}
        >
          <UnderlineIcon className="h-3.5 w-3.5" />
          Underline
        </Button>
        <Button
          type="button"
          size="sm"
          variant={editor?.isActive('bulletList') ? 'default' : 'outline'}
          className={toolbarButtonClass}
          onClick={() => editor?.chain().focus().toggleBulletList().run()}
          disabled={!editor || disabled}
        >
          <List className="h-3.5 w-3.5" />
          Bullets
        </Button>
        <Button
          type="button"
          size="sm"
          variant={editor?.isActive('orderedList') ? 'default' : 'outline'}
          className={toolbarButtonClass}
          onClick={() => editor?.chain().focus().toggleOrderedList().run()}
          disabled={!editor || disabled}
        >
          <ListOrdered className="h-3.5 w-3.5" />
          Numbered
        </Button>
        <Button
          type="button"
          size="sm"
          variant={editor?.isActive('link') ? 'default' : 'outline'}
          className={toolbarButtonClass}
          onClick={setLink}
          disabled={!editor || disabled}
        >
          <Link2 className="h-3.5 w-3.5" />
          Link
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className={toolbarButtonClass}
          onClick={() => editor?.chain().focus().unsetLink().run()}
          disabled={!editor || disabled || !editor.isActive('link')}
        >
          <Unlink className="h-3.5 w-3.5" />
          Unlink
        </Button>
      </div>

      <div data-testid="reviewer-email-compose-editor">
        <EditorContent editor={editor} />
      </div>
    </div>
  )
}
