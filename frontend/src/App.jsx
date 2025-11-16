import { useState, useEffect } from 'react'
import './App.css'

/**
 * App 组件：提供音频上传与基础查询的演示界面。
 * 无参数。
 * 返回值：React 组件用于渲染应用。
 */
function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '')
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState('')

  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [chunks, setChunks] = useState([])
  const [loadingQuery, setLoadingQuery] = useState(false)

  const [episodeIdForTranscript, setEpisodeIdForTranscript] = useState('')
  const [transcript, setTranscript] = useState('')
  const [taskId, setTaskId] = useState(null)
  const [taskStatus, setTaskStatus] = useState('')

  // URL摄入
  const [urlInput, setUrlInput] = useState('')
  const [urlTaskId, setUrlTaskId] = useState(null)
  const [urlTaskStatus, setUrlTaskStatus] = useState('')
  const [urlTaskObj, setUrlTaskObj] = useState(null)
  const [autoRefreshUrl, setAutoRefreshUrl] = useState(true)
  const [urlTaskHistory, setUrlTaskHistory] = useState([])

  /**
   * 根据状态映射进度与颜色。
   * @param {string} st - 任务状态
   * @returns {{pct:number,color:string,label:string}}
   */
  const statusMeta = (st) => {
    const map = {
      pending: { pct: 10, color: '#9aa5b1', label: '已提交' },
      downloading: { pct: 30, color: '#2f81f7', label: '下载中' },
      transcribing: { pct: 60, color: '#b07ceb', label: '转写中' },
      processing: { pct: 80, color: '#f59e0b', label: '处理中' },
      succeeded: { pct: 100, color: '#10b981', label: '完成' },
      failed: { pct: 100, color: '#ef4444', label: '失败' },
    }
    return map[st] || { pct: 0, color: '#9aa5b1', label: st || '未知' }
  }

  /**
   * 登录，获取JWT。
   * @returns {Promise<void>} 无返回值。
   */
  const handleLogin = async () => {
    const username = prompt('请输入用户名（如：admin）')
    const password = prompt('请输入密码（测试可随意）')
    if (!username || !password) return
    const resp = await fetch('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
    if (resp.status === 401) {
      // 尝试注册后再登录
      await fetch('http://localhost:8000/auth/register', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role: 'creator' })
      })
      const resp2 = await fetch('http://localhost:8000/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })
      if (!resp2.ok) { alert('登录失败'); return }
      const data2 = await resp2.json()
      localStorage.setItem('token', data2.access_token)
      setToken(data2.access_token)
      return
    }
    if (!resp.ok) { alert('登录失败'); return }
    const data = await resp.json()
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
  }

  /**
   * 处理音频文件上传。
   * @param {Event} e - input[file] 的变更事件。
   * @returns {Promise<void>} 无返回值。
   */
  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadMsg('')
    try {
      const form = new FormData()
      form.append('file', file)
      const resp = await fetch('http://localhost:8000/upload/audio', {
        method: 'POST',
        body: form,
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
      if (!resp.ok) throw new Error('上传失败')
      const data = await resp.json()
      setUploadMsg(`${data.message} | 节目ID: ${data.episode.id}`)
    } catch (err) {
      setUploadMsg(`上传失败：${err.message}`)
    } finally {
      setUploading(false)
    }
  }

  /**
   * 提交查询请求到后端。
   * 无参数。
   * @returns {Promise<void>} 无返回值。
   */
  const submitQuery = async () => {
    if (!question.trim()) return
    setLoadingQuery(true)
    setAnswer('')
    setChunks([])
    try {
      const resp = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, top_k: 3 }),
      })
      if (!resp.ok) throw new Error('查询失败')
      const data = await resp.json()
      setAnswer(data.answer)
      setChunks(data.chunks || [])
    } catch (err) {
      setAnswer(`查询失败：${err.message}`)
    } finally {
      setLoadingQuery(false)
    }
  }

  /**
   * 提交转录文本进行处理。
   * @returns {Promise<void>}
   */
  const submitTranscript = async () => {
    if (!episodeIdForTranscript || !transcript.trim()) return
    const resp = await fetch('http://localhost:8000/episodes/transcript', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ episode_id: Number(episodeIdForTranscript), transcript })
    })
    if (!resp.ok) { alert('提交失败'); return }
    const data = await resp.json()
    setTaskId(data.task_id)
    setTaskStatus('pending')
  }

  /**
   * 轮询任务状态。
   */
  const pollTask = async () => {
    if (!taskId) return
    const resp = await fetch(`http://localhost:8000/episodes/tasks/${taskId}`)
    if (!resp.ok) return
    const data = await resp.json()
    setTaskStatus(`${data.status} | ${data.message}`)
  }

  /**
   * 确保有有效登录令牌：若不存在或失效则自动注册/登录 demo。
   * 无参数。
   * 返回值：Promise<void>
   */
  const ensureAuth = async () => {
    let tk = localStorage.getItem('token') || ''
    // 若已有令牌，尝试校验
    if (tk) {
      try {
        const ping = await fetch('http://localhost:8000/auth/me', {
          headers: { 'Authorization': `Bearer ${tk}` }
        })
        if (ping.ok) return
      } catch (_) { /* 忽略网络错误，继续走自动登录 */ }
    }
    // 自动注册/登录 demo 账号
    const username = 'demo'
    const password = 'demo'
    try {
      await fetch('http://localhost:8000/auth/register', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, role: 'creator' })
      })
    } catch (_) { /* 用户可能已存在，忽略 */ }
    const resp = await fetch('http://localhost:8000/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
    if (!resp.ok) throw new Error('自动登录失败')
    const data = await resp.json()
    localStorage.setItem('token', data.access_token)
    setToken(data.access_token)
  }

  /**
   * 提交视频URL进行异步摄入。
   * @returns {Promise<void>} 无返回值。
   */
  const submitUrlIngest = async () => {
    if (!urlInput.trim()) return
    try {
      // 保证鉴权有效
      await ensureAuth()
      const tk = localStorage.getItem('token') || ''
      // 标准化URL：无协议时自动加 https://
      let submitUrl = urlInput.trim()
      if (!/^https?:\/\//i.test(submitUrl)) {
        submitUrl = 'https://' + submitUrl.replace(/^\/\//, '')
      }
      const resp = await fetch('http://localhost:8000/intake/submit_url', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(tk ? { 'Authorization': `Bearer ${tk}` } : {})
        },
        body: JSON.stringify({ url: submitUrl })
      })
      if (!resp.ok) {
        let msg = '提交URL失败'
        try {
          const err = await resp.json()
          const detail = (typeof err === 'string') ? err : (err.detail || JSON.stringify(err))
          msg += `：${detail}`
        } catch (_) { msg += `：HTTP ${resp.status}` }
        alert(msg)
        return
      }
      const data = await resp.json()
      setUrlTaskId(data.task_id)
      setUrlTaskStatus('pending')
      setUrlTaskObj({ id: data.task_id, status: 'pending', message: '已提交，排队中' })
      setUrlTaskHistory((h) => [...h, { ts: Date.now(), status: 'pending', message: '已提交，排队中' }])
    } catch (e) {
      alert(`提交URL失败：${e.message}`)
    }
  }

  /**
   * 轮询URL摄入任务状态。
   */
  const pollUrlTask = async () => {
    if (!urlTaskId) return
    const resp = await fetch(`http://localhost:8000/tasks/${urlTaskId}`)
    if (!resp.ok) return
    const data = await resp.json()
    setUrlTaskStatus(`${data.status} | ${data.message}${data.episode_id ? ' | Episode ' + data.episode_id : ''}`)
    setUrlTaskObj(data)
    setUrlTaskHistory((h) => {
      const last = h[h.length - 1]
      if (!last || last.status !== data.status || last.message !== data.message) {
        return [...h, { ts: Date.now(), status: data.status, message: data.message }]
      }
      return h
    })
  }

  // 自动轮询：当启用自动刷新且存在任务ID时，每2秒轮询一次直到终态
  useEffect(() => {
    if (!autoRefreshUrl || !urlTaskId) return
    const isTerminal = (s) => s === 'succeeded' || s === 'failed'
    const timer = setInterval(() => {
      const st = urlTaskObj?.status
      if (st && isTerminal(st)) { clearInterval(timer); return }
      pollUrlTask()
    }, 2000)
    return () => clearInterval(timer)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefreshUrl, urlTaskId, urlTaskObj?.status])

  return (
    <div className="container">
      <header>
        <div>
          <h1>Cognito · 科普/知识主播知识库</h1>
          <p>登录后上传音频，提交转录文本进行处理，并进行向量检索查询。</p>
        </div>
        <div>
          <button onClick={handleLogin}>{token ? '已登录' : '登录/注册'}</button>
        </div>
      </header>

      <div className="layout">
        <div className="col-left">
          <section className="card">
            <h2>提交视频URL进行摄入</h2>
            <div className="row" style={{ gap: 12 }}>
              <input type="text" value={urlInput} onChange={(e) => setUrlInput(e.target.value)} placeholder="粘贴B站/油管/抖音/TikTok链接" />
              <button onClick={submitUrlIngest} disabled={!token}>提交</button>
            </div>
            <div style={{ marginTop: 8 }}>
              <button onClick={pollUrlTask} disabled={!urlTaskId}>刷新任务状态</button>
              <label style={{ marginLeft: 12 }}>
                <input type="checkbox" checked={autoRefreshUrl} onChange={(e) => setAutoRefreshUrl(e.target.checked)} /> 自动刷新
              </label>
            </div>
            {urlTaskObj && (
              <div className="status-panel">
                <div className="status-header">
                  <span className="badge" style={{ background: statusMeta(urlTaskObj.status).color }}>
                    {statusMeta(urlTaskObj.status).label}
                  </span>
                  <span style={{ marginLeft: 12, color: '#9aa5b1' }}>{urlTaskObj.message}</span>
                  {urlTaskObj.episode_id ? (
                    <span style={{ marginLeft: 12, color: '#9aa5b1' }}>
                      Episode {urlTaskObj.episode_id}
                    </span>
                  ) : null}
                </div>
                <div className="progress">
                  <div className="bar" style={{ width: `${statusMeta(urlTaskObj.status).pct}%`, background: statusMeta(urlTaskObj.status).color }} />
                </div>
                <div className="timeline">
                  {urlTaskHistory.slice(-8).map((it, i) => (
                    <div key={i} className="timeline-item">
                      <span className="dot" style={{ background: statusMeta(it.status).color }} />
                      <span className="text">{new Date(it.ts).toLocaleTimeString()} · {statusMeta(it.status).label} · {it.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
          <section className="card">
            <h2>上传音频文件</h2>
            <input type="file" accept=".mp3,.mp4,.wav,.m4a" onChange={handleUpload} disabled={uploading} />
            <p style={{ marginTop: 8, color: '#9aa5b1' }}>{uploading ? '正在上传...' : uploadMsg}</p>
          </section>

          <section className="card">
            <h2>提交转录文本（替代ASR演示）</h2>
            <div className="row" style={{ gap: 12 }}>
              <input type="number" value={episodeIdForTranscript} onChange={(e) => setEpisodeIdForTranscript(e.target.value)} placeholder="节目ID" />
            </div>
            <textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} rows={6} style={{ width: '100%', marginTop: 8 }} placeholder="在此粘贴转录文本" />
            <div style={{ marginTop: 8 }}>
              <button onClick={submitTranscript} disabled={!token}>提交处理</button>
              <button onClick={pollTask} style={{ marginLeft: 12 }} disabled={!taskId}>刷新任务状态</button>
              <span style={{ marginLeft: 12, color: '#9aa5b1' }}>{taskStatus}</span>
            </div>
          </section>
        </div>

        <div className="col-right">
          <section className="card">
            <h2>查询知识库（向量检索优先）</h2>
            <div className="row" style={{ gap: 12 }}>
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="请输入问题，如：量子纠缠的定义是什么？"
                style={{ flex: 1 }}
              />
              <button onClick={submitQuery} disabled={loadingQuery}>
                {loadingQuery ? '查询中...' : '查询'}
              </button>
            </div>
            {answer && (
              <div className="answer" style={{ marginTop: 12 }}>
                <h3>答案</h3>
                <pre style={{ whiteSpace: 'pre-wrap' }}>{answer}</pre>
              </div>
            )}
            {!!chunks.length && (
              <div className="chunks" style={{ marginTop: 12 }}>
                <h3>相关知识块</h3>
                <ul>
                  {chunks.map((c) => (
                    <li key={c.id}>
                      <strong>Chunk #{c.id}</strong>（Episode {c.episode_id}）
                      <div style={{ opacity: 0.8 }}>时间：{c.start_time ?? '-'} ~ {c.end_time ?? '-'}</div>
                      <div>{c.text}</div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        </div>
      </div>

      <footer style={{ marginTop: 16 }}>
        <small>已支持登录、转录处理、向量检索；后续接入 ASR 与重排序。</small>
      </footer>
    </div>
  )
}

export default App
