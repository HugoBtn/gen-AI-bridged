import { BriefcaseBusiness, User, Building2, Mail, Phone, Users } from 'lucide-react'

// Everything the backend query parser understands (see app/orchestrator.py).
// `patterns` are templates shown as read-only code — they need a value from your
// own org to be useful. `examples` are safe to run as-is against the seed data,
// so the UI renders them as clickable chips.
export const SEARCH_RECIPES = [
  {
    id: 'title',
    icon: BriefcaseBusiness,
    label: 'By job title',
    hint: 'Any role word works: Director, Manager, CTO, VP, Head, Engineer, Sales, Marketing, Operations…',
    patterns: ['find a <title>', 'title <title>'],
    examples: ['find a Director', 'find a Manager', 'find a CTO', 'find a VP', 'find an Engineer'],
  },
  {
    id: 'name',
    icon: User,
    label: 'By name',
    hint: 'Full or partial name — the words can be in any order.',
    patterns: ['find <first last>', 'who is <name>', 'find someone named <name>'],
    examples: [],
  },
  {
    id: 'company',
    icon: Building2,
    label: 'By company',
    hint: 'Lead with “at”, “from” or “company”, then the account name.',
    patterns: ['who works at <company>', 'find someone from <company>', 'company <name>'],
    examples: [],
  },
  {
    id: 'email',
    icon: Mail,
    label: 'By email',
    hint: 'A full address, or just the part you remember.',
    patterns: ['who is <name@company.com>', 'find <name@company.com>'],
    examples: [],
  },
  {
    id: 'phone',
    icon: Phone,
    label: 'By phone',
    hint: 'Any run of digits from the phone or mobile field.',
    patterns: ['find <03-1234-5678>', 'find <555 0134>'],
    examples: [],
  },
  {
    id: 'narrow',
    icon: Users,
    label: 'Contacts vs leads',
    hint: 'Add “contact” or “lead” to any search to narrow the record type. Filters stack — mix a title, a company and a type in one question.',
    patterns: ['find a <title> lead', 'contacts at <company>', 'find a <title> at <company>'],
    examples: ['find a Director lead', 'find a Manager contact', 'leads in Marketing'],
  },
]

// Shown as chips under the chat. The first few are always visible; the rest sit
// behind the “More” toggle so the message list keeps its room.
export const QUICK_SUGGESTIONS = ['find a Director', 'find a Manager', 'who works in Sales']

export const MORE_SUGGESTIONS = [
  'find a CTO',
  'find a VP',
  'find an Engineer',
  'find someone in Operations',
  'find a Director lead',
  'find a Manager contact',
]
