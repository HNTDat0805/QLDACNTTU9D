import { isAxiosError } from "axios"

type UnknownRecord = Record<string, unknown>

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === "object" && value !== null

const getFastApiDetail = (error: unknown): unknown => {
  if (!isAxiosError(error) || !isRecord(error.response?.data)) {
    return undefined
  }

  return error.response.data.detail
}

const getFieldName = (location: unknown): string | undefined => {
  if (!Array.isArray(location)) {
    return undefined
  }

  const parts = location.filter(
    (part): part is string | number =>
      (typeof part === "string" || typeof part === "number") && part !== "body",
  )

  return parts.length > 0 ? parts.join(".") : undefined
}

export const getApiErrorStatus = (error: unknown): number | undefined =>
  isAxiosError(error) ? error.response?.status : undefined

export const getValidationErrors = (error: unknown): Record<string, string> => {
  const detail = getFastApiDetail(error)
  if (!Array.isArray(detail)) {
    return {}
  }

  return detail.reduce<Record<string, string>>((fieldErrors, item) => {
    if (!isRecord(item) || typeof item.msg !== "string") {
      return fieldErrors
    }

    const fieldName = getFieldName(item.loc)
    if (fieldName && !fieldErrors[fieldName]) {
      fieldErrors[fieldName] = item.msg
    }

    return fieldErrors
  }, {})
}

export const getApiErrorMessage = (error: unknown): string => {
  const status = getApiErrorStatus(error)
  const detail = getFastApiDetail(error)

  if (status === 422) {
    const [fieldName, message] =
      Object.entries(getValidationErrors(error))[0] ?? []
    if (fieldName && message) {
      return `${fieldName}: ${message}`
    }
    return "Dữ liệu gửi lên không hợp lệ. Vui lòng kiểm tra lại các trường."
  }

  if (status === 403) {
    return "Bạn không có quyền thực hiện thao tác này."
  }

  if (status === 404) {
    return "Không tìm thấy dữ liệu bạn yêu cầu."
  }

  if (status !== undefined && status >= 500) {
    return "Máy chủ đang gặp sự cố. Vui lòng thử lại sau."
  }

  if (isAxiosError(error) && !error.response) {
    return "Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối và thử lại."
  }

  if (typeof detail === "string") {
    return detail
  }

  if (status === 401) {
    return "Phiên đăng nhập không hợp lệ hoặc đã hết hạn."
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return "Đã xảy ra lỗi không xác định. Vui lòng thử lại."
}

export const handleError = function (
  this: (msg: string) => void,
  error: unknown,
) {
  this(getApiErrorMessage(error))
}

export const getInitials = (name: string): string => {
  return name
    .split(" ")
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase()
}
