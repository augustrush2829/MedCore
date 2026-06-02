export const STAFF_TOKEN_COOKIE = 'medcore.staff.token'

export type StaffUser = {
  id: string
  name: string
  email: string
  role: string
  organization_id: string
  organization_name?: string | null
}
