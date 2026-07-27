import { Briefcase, Building2 } from 'lucide-react'
import { initials } from '../utils'

export default function PersonCard({ person, onClick }) {
  const isLead = person.type === 'Lead'
  return (
    <button className="person-card" onClick={onClick}>
      <div className="person-card__top">
        <div className="avatar">{initials(person.name)}</div>
        <span className={'badge ' + (isLead ? 'badge--lead' : 'badge--contact')}>
          {person.type}
        </span>
      </div>
      <div className="person-card__name">{person.name || 'Unknown'}</div>
      <div className="person-card__meta">
        <Briefcase size={14} />
        <span>{person.title || '—'}</span>
      </div>
      <div className="person-card__meta">
        <Building2 size={14} />
        <span>{person.company || '—'}</span>
      </div>
    </button>
  )
}
