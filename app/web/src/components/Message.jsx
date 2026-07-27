import { Bot, User } from 'lucide-react'

export default function Message({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={'msg ' + (isUser ? 'msg--user' : 'msg--bot')}>
      {!isUser && (
        <div className="msg__avatar msg__avatar--bot">
          <Bot size={16} />
        </div>
      )}
      <div className={'msg__bubble' + (message.error ? ' msg__bubble--error' : '')}>
        {message.text}
      </div>
      {isUser && (
        <div className="msg__avatar msg__avatar--user">
          <User size={16} />
        </div>
      )}
    </div>
  )
}
