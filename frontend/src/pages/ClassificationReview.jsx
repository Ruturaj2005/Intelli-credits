/**
 * ClassificationReview - Human-in-the-loop document classification review
 * Shows AI-detected document types with confidence scores and allows user override
 */
import { useState, useEffect } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import axios from 'axios'
import {
  FileText,
  CheckCircle2,
  AlertCircle,
  Edit3,
  TrendingUp,
  Eye,
  ArrowRight,
  Shield,
  Zap,
} from 'lucide-react'

const API = '/api'

// All possible document types for override dropdown
const DOCUMENT_TYPES = [
  'ALM',
  'SHAREHOLDING_PATTERN',
  'BORROWING_PROFILE',
  'PORTFOLIO_PERFORMANCE',
  'ANNUAL_REPORT',
  'FINANCIAL_STATEMENT',
  'BANK_STATEMENT',
  'GST_RETURN',
  'CIBIL_REPORT',
  'ITR',
  'LEGAL_DOCUMENT',
  'MCA_FILING',
  'RATING_REPORT',
  'SANCTION_LETTER',
  'UNKNOWN',
]

// Format document type for display
const formatDocType = (type) => {
  return type
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (l) => l.toUpperCase())
}

// Format file size
const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Get confidence badge styling
const getConfidenceBadge = (level, userModified) => {
  if (userModified) {
    return {
      bg: 'var(--accent2)20',
      color: 'var(--accent2)',
      border: 'var(--accent2)',
      label: 'Manually Set',
    }
  }

  switch (level) {
    case 'HIGH':
      return {
        bg: 'var(--success)20',
        color: 'var(--success)',
        border: 'var(--success)',
        label: 'High Confidence',
      }
    case 'MEDIUM':
      return {
        bg: 'var(--warning)20',
        color: 'var(--warning)',
        border: 'var(--warning)',
        label: 'Medium Confidence',
      }
    case 'LOW':
      return {
        bg: 'var(--danger)20',
        color: 'var(--danger)',
        border: 'var(--danger)',
        label: 'Low Confidence',
      }
    default:
      return {
        bg: 'var(--muted)20',
        color: 'var(--muted)',
        border: 'var(--muted)',
        label: 'Unknown',
      }
  }
}

export default function ClassificationReview() {
  const navigate = useNavigate()
  const { applicationId } = useParams()
  const location = useLocation()
  
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [classificationData, setClassificationData] = useState(null)
  const [qualitativeInputs, setQualitativeInputs] = useState(null)
  const [userOverrides, setUserOverrides] = useState({})
  const [userComments, setUserComments] = useState({})

  // Load classification data from navigation state
  useEffect(() => {
    // Get data passed from NewAppraisal via navigate state
    const state = location.state
    
    if (!state || !state.classificationData) {
      setError('No classification data found. Please upload documents first.')
      return
    }
    
    setClassificationData(state.classificationData)
    setQualitativeInputs(state.qualitativeInputs || null)
  }, [applicationId, location])

  // Handle document type override
  const handleOverride = (fileId, newType) => {
    setUserOverrides((prev) => ({
      ...prev,
      [fileId]: newType,
    }))
  }

  // Handle comment change
  const handleCommentChange = (fileId, comment) => {
    setUserComments((prev) => ({
      ...prev,
      [fileId]: comment,
    }))
  }

  // Check if ready to submit
  const canSubmit = () => {
    if (!classificationData) return false

    // All UNKNOWN documents must be manually classified
    return classificationData.detected_documents.every((doc) => {
      const finalType = userOverrides[doc.file_id] || doc.auto_classification
      return finalType !== 'UNKNOWN'
    })
  }

  // Submit confirmed classifications
  const handleConfirmAndStart = async () => {
    if (!canSubmit()) {
      setError('Please classify all UNKNOWN documents before proceeding')
      return
    }

    // Build updated classification data with user overrides
    const updatedDetectedDocs = classificationData.detected_documents.map((doc) => ({
      ...doc,
      auto_classification: userOverrides[doc.file_id] || doc.auto_classification,
      user_modified: !!userOverrides[doc.file_id],
      user_comment: userComments[doc.file_id] || null,
    }))

    const updatedClassificationData = {
      ...classificationData,
      detected_documents: updatedDetectedDocs,
    }

    // Navigate to schema selection with classification data
    navigate(`/appraisal/${applicationId}/schema-config`, {
      state: {
        classificationData: updatedClassificationData,
        qualitativeInputs: qualitativeInputs,
        userOverrides: userOverrides,
      }
    })
  }

  if (!classificationData) {
    return (
      <div className="max-w-6xl mx-auto px-8 py-10">
        <div className="flex items-center justify-center h-64">
          <div className="spinner" style={{ width: '40px', height: '40px' }}></div>
        </div>
      </div>
    )
  }

  const autoAcceptCount = classificationData.auto_accept_count
  const reviewRequiredCount = classificationData.review_required_count

  return (
    <div className="max-w-6xl mx-auto px-8 py-10">
      {/* Header */}
      <div className="mb-10 animate-slide-up">
        <div className="flex items-center gap-3 mb-3">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-dark))' }}
          >
            <Eye size={24} color="white" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="font-syne font-bold text-3xl" style={{ color: 'var(--text)' }}>
              Review Document Classifications
            </h1>
            <p className="text-sm mt-0.5" style={{ color: 'var(--muted)' }}>
              AI has analyzed your documents. Confirm or correct before analysis begins.
            </p>
          </div>
        </div>

        {/* Innovation Badge */}
        <div
          className="mt-6 p-4 rounded-lg flex items-start gap-3 border"
          style={{
            background: 'var(--accent)10',
            borderColor: 'var(--accent)',
          }}
        >
          <Shield size={20} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: '2px' }} />
          <div>
            <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text)' }}>
              <Zap
                size={14}
                className="inline mr-1"
                style={{ color: 'var(--accent)', marginTop: '-2px' }}
              />
              Human-in-the-Loop AI Decision Making
            </p>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>
              Our AI classifier provides confidence scores and reasoning for every document. You have
              full control to override any classification before automated extraction begins.
            </p>
          </div>
        </div>
      </div>

      {/* Document Cards */}
      <div className="space-y-4 mb-8">
        {classificationData.detected_documents.map((doc, idx) => {
          const finalType = userOverrides[doc.file_id] || doc.auto_classification
          const userModified = !!userOverrides[doc.file_id]
          const badge = getConfidenceBadge(doc.confidence_label, userModified)

          return (
            <div
              key={doc.file_id}
              className="card p-6 animate-scale-in"
              style={{ animationDelay: `${idx * 50}ms` }}
            >
              <div className="grid grid-cols-12 gap-6 items-center">
                {/* LEFT: File Info */}
                <div className="col-span-3 flex items-center gap-3">
                  <div
                    className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: 'var(--surface-elevated)' }}
                  >
                    <FileText size={20} style={{ color: 'var(--accent)' }} />
                  </div>
                  <div className="min-w-0">
                    <p
                      className="text-sm font-semibold truncate"
                      style={{ color: 'var(--text)' }}
                      title={doc.file_name}
                    >
                      {doc.file_name}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>
                      {formatFileSize(doc.file_size)}
                    </p>
                  </div>
                </div>

                {/* CENTER: Classification Info */}
                <div className="col-span-5">
                  <div className="flex items-center gap-2 mb-2">
                    <div
                      className="px-3 py-1 rounded-full text-xs font-bold border"
                      style={{
                        background: badge.bg,
                        color: badge.color,
                        borderColor: badge.border,
                      }}
                    >
                      {formatDocType(finalType)}
                    </div>
                    {userModified && (
                      <div
                        className="px-2 py-0.5 rounded text-xs font-semibold"
                        style={{ background: 'var(--accent2)20', color: 'var(--accent2)' }}
                      >
                        <Edit3 size={10} className="inline mr-1" style={{ marginTop: '-2px' }} />
                        User Override
                      </div>
                    )}
                  </div>

                  {/* Confidence Bar */}
                  {!userModified && (
                    <>
                      <div className="flex items-center gap-3 mb-2">
                        <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--surface-elevated)' }}>
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${doc.confidence * 100}%`,
                              background: badge.border,
                            }}
                          ></div>
                        </div>
                        <span className="text-xs font-mono font-semibold" style={{ color: badge.color }}>
                          {(doc.confidence * 100).toFixed(0)}%
                        </span>
                      </div>

                      {/* Reasoning */}
                      <p className="text-xs italic" style={{ color: 'var(--muted)' }}>
                        {doc.classification_reasoning}
                      </p>
                    </>
                  )}
                </div>

                {/* RIGHT: Override Controls */}
                <div className="col-span-4">
                  <label className="input-label text-xs mb-2">
                    {userModified ? 'Overridden Type' : 'Override Classification'}
                  </label>
                  <select
                    className="input-field text-sm"
                    value={finalType}
                    onChange={(e) => handleOverride(doc.file_id, e.target.value)}
                  >
                    {DOCUMENT_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {formatDocType(type)}
                      </option>
                    ))}
                  </select>

                  {userModified && (
                    <div className="mt-2">
                      <input
                        type="text"
                        className="input-field text-xs"
                        placeholder="Optional comment on override..."
                        value={userComments[doc.file_id] || ''}
                        onChange={(e) => handleCommentChange(doc.file_id, e.target.value)}
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Show alternatives if available and not user-modified */}
              {!userModified && doc.alternative_classifications.length > 0 && (
                <div className="mt-4 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
                  <p className="text-xs font-semibold mb-2" style={{ color: 'var(--muted)' }}>
                    Alternative Classifications:
                  </p>
                  <div className="flex gap-2">
                    {doc.alternative_classifications.map((alt) => (
                      <div
                        key={alt.type}
                        className="px-2 py-1 rounded text-xs"
                        style={{ background: 'var(--surface-elevated)', color: 'var(--muted)' }}
                      >
                        {formatDocType(alt.type)} ({(alt.confidence * 100).toFixed(0)}%)
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        <div
          className="card p-6 border"
          style={{ borderColor: 'var(--success)', background: 'var(--success)05' }}
        >
          <div className="flex items-center gap-3">
            <CheckCircle2 size={32} style={{ color: 'var(--success)' }} />
            <div>
              <p className="text-2xl font-bold" style={{ color: 'var(--text)' }}>
                {autoAcceptCount}
              </p>
              <p className="text-sm" style={{ color: 'var(--muted)' }}>
                Documents auto-accepted (confidence ≥ 70%)
              </p>
            </div>
          </div>
        </div>

        <div
          className="card p-6 border"
          style={{
            borderColor: reviewRequiredCount > 0 ? 'var(--warning)' : 'var(--success)',
            background: reviewRequiredCount > 0 ? 'var(--warning)05' : 'var(--success)05',
          }}
        >
          <div className="flex items-center gap-3">
            <AlertCircle
              size={32}
              style={{ color: reviewRequiredCount > 0 ? 'var(--warning)' : 'var(--success)' }}
            />
            <div>
              <p className="text-2xl font-bold" style={{ color: 'var(--text)' }}>
                {reviewRequiredCount}
              </p>
              <p className="text-sm" style={{ color: 'var(--muted)' }}>
                {reviewRequiredCount > 0 ? 'Documents need your review' : 'All documents confident'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div
          className="card p-5 border-2 animate-scale-in mb-8"
          style={{ borderColor: 'var(--danger)', background: 'var(--danger)10' }}
        >
          <div className="flex items-start gap-3">
            <div
              className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ background: 'var(--danger)20' }}
            >
              <span style={{ color: 'var(--danger)' }}>!</span>
            </div>
            <div>
              <p className="text-sm font-semibold mb-1" style={{ color: 'var(--danger)' }}>
                Validation Error
              </p>
              <p className="text-xs" style={{ color: 'var(--danger-dark)' }}>
                {error}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* CTA Button */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate('/dashboard')}
          className="btn-secondary"
        >
          ← Cancel
        </button>
        <button
          type="button"
          onClick={handleConfirmAndStart}
          disabled={!canSubmit()}
          className="btn-primary flex items-center gap-3 px-10"
        >
          <span>Next: Configure Extraction Schemas</span>
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  )
}
