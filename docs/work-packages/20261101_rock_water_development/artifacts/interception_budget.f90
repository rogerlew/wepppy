! Original research implementation: conserve represented interception supply.
! Inputs and persisted stores are native default REAL; allocation arithmetic
! uses DOUBLE PRECISION. Callers supply finite nonnegative depths/capacities.
subroutine wb_interception_allocate(rain, melt, irrigation, carry, plant, residue)
  implicit none
  real, intent(in) :: rain, melt, irrigation, carry
  real, intent(inout) :: plant, residue
  double precision :: owned, room

  owned = ((dble(rain) + dble(melt)) + dble(irrigation)) + dble(carry)
  if (owned <= dble(plant)) then
    plant = real(owned)
    if (dble(plant) > owned) plant = nearest(plant, -1.0)
    residue = 0.0
  else if (owned <= dble(plant) + dble(residue)) then
    room = owned - dble(plant)
    residue = real(room)
    if (dble(residue) > room) residue = nearest(residue, -1.0)
  end if
end subroutine wb_interception_allocate

! Signed remainder: positive throughfall or negative net interception when
! called with zero incoming supply. Never floor a physical withdrawal.
double precision function wb_interception_remaining(supply, carry, plant, residue)
  implicit none
  double precision, intent(in) :: supply
  real, intent(in) :: carry, plant, residue
  wb_interception_remaining = ((supply + dble(carry)) - dble(plant)) - dble(residue)
end function wb_interception_remaining
