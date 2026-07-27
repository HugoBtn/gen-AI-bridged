import {
  ArrowLeft,
  Mail,
  Phone,
  Smartphone,
  MapPin,
  Building2,
  Briefcase,
  User,
  Calendar,
  Tag,
  TrendingUp,
  LifeBuoy,
} from 'lucide-react'
import { initials, money, shortDate, joinLocation } from '../utils'

function Field({ icon: Icon, label, value }) {
  return (
    <div className="field">
      <Icon size={15} className="field__icon" />
      <div>
        <div className="field__label">{label}</div>
        <div className="field__value">{value || '—'}</div>
      </div>
    </div>
  )
}

export default function PersonDetail({ person, onBack }) {
  const isLead = person.type === 'Lead'
  const opps = person.opportunities || []
  const cases = person.cases || []

  return (
    <div className="detail">
      <button className="detail__back" onClick={onBack}>
        <ArrowLeft size={16} /> Back to results
      </button>

      <div className="detail__head">
        <div className="avatar detail__avatar">{initials(person.name)}</div>
        <div>
          <h2 className="detail__name">
            {person.name || 'Unknown'}
            <span className={'badge ' + (isLead ? 'badge--lead' : 'badge--contact')}>
              {person.type}
            </span>
          </h2>
          <p className="detail__role">
            {[person.title, person.company].filter(Boolean).join(' · ') || '—'}
          </p>
        </div>
      </div>

      <div className="detail__card">
        <h3 className="detail__card-title">Contact information</h3>
        <div className="fields">
          <Field icon={Mail} label="Email" value={person.email} />
          <Field icon={Phone} label="Phone" value={person.phone} />
          <Field icon={Smartphone} label="Mobile" value={person.mobile} />
          <Field icon={MapPin} label="Location" value={joinLocation(person.city, person.country)} />
          <Field icon={Building2} label="Company" value={person.company} />
          <Field icon={Briefcase} label="Department" value={person.department} />
          <Field icon={Tag} label="Industry" value={person.industry} />
          <Field icon={User} label="Owner" value={person.owner} />
          {isLead && <Field icon={Tag} label="Status" value={person.status} />}
          {isLead && <Field icon={Tag} label="Lead source" value={person.leadSource} />}
          <Field icon={Calendar} label="Created" value={shortDate(person.createdDate)} />
        </div>
      </div>

      {!isLead && (
        <div className="detail__card">
          <h3 className="detail__card-title">
            <TrendingUp size={14} style={{ verticalAlign: '-2px', marginRight: 6 }} />
            Opportunities on this account ({opps.length})
          </h3>
          {opps.length === 0 ? (
            <div className="detail__empty">No opportunities on this account.</div>
          ) : (
            <div className="rows">
              {opps.map((o, i) => (
                <div className="row" key={i}>
                  <div className="row__main">
                    <div className="row__title">{o.name || 'Untitled'}</div>
                    <div className="row__sub">
                      {o.stage || '—'} · closes {shortDate(o.closeDate)}
                    </div>
                  </div>
                  <span className={'pill ' + (o.isClosed ? 'pill--closed' : 'pill--open')}>
                    {o.isClosed ? 'Closed' : 'Open'}
                  </span>
                  <span className="row__amount">{money(o.amount)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!isLead && (
        <div className="detail__card">
          <h3 className="detail__card-title">
            <LifeBuoy size={14} style={{ verticalAlign: '-2px', marginRight: 6 }} />
            Cases linked to this contact ({cases.length})
          </h3>
          {cases.length === 0 ? (
            <div className="detail__empty">No cases linked to this contact.</div>
          ) : (
            <div className="rows">
              {cases.map((c, i) => (
                <div className="row" key={i}>
                  <div className="row__main">
                    <div className="row__title">{c.subject || 'Untitled'}</div>
                    <div className="row__sub">
                      {c.status || '—'} · {c.priority || '—'} priority · {shortDate(c.createdDate)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
