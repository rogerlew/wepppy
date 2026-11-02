! Original research candidate. Exact expansion of represented native depths.
! Strict binary64 operations are required; do not enable reassociation/fast-math.
! Native REAL inputs are finite binary32. Six such terms cannot overflow binary64,
! and their smallest nonzero lattice (2**-149) cannot underflow binary64.
module interception_expansion
  implicit none
contains
  double precision function exact_sum(n, terms) result(total)
    integer, intent(in) :: n
    double precision, intent(in) :: terms(n)
    double precision :: expansion(8), grown(8), q, s, bv, av, br, ar, error
    integer :: i, j, length, count
    length=0
    do i=1,n
      q=terms(i)
      count=0
      do j=1,length
        ! Error-free TwoSum: q + expansion(j) = s + error exactly.
        s=q+expansion(j)
        bv=s-q
        av=s-bv
        br=expansion(j)-bv
        ar=q-av
        error=ar+br
        if (error /= 0.d0) then
          count=count+1
          grown(count)=error
        end if
        q=s
      end do
      count=count+1
      grown(count)=q
      expansion(:count)=grown(:count)
      length=count
    end do
    ! Components are ordered/nonoverlapping; cancellation has already occurred.
    ! The rounded sum retains exact sign, including tiny cancellation residues.
    total=0.d0
    do j=1,length
      total=total+expansion(j)
    end do
  end function exact_sum

  real function bounded_store(n, terms) result(value)
    integer, intent(in) :: n
    double precision, intent(in) :: terms(n)
    double precision :: difference, check(8)
    real :: successor
    check(:n)=terms
    value=real(exact_sum(n,terms))
    check(n+1)=-dble(value)
    difference=exact_sum(n+1,check(:n+1))
    if (difference < 0.d0) value=nearest(value,-1.0)
    ! Certify both budget feasibility and maximal representable acceptance.
    check(n+1)=-dble(value)
    if (exact_sum(n+1,check(:n+1)) < 0.d0) error stop 'INTERCEPTION OVERDRAW'
    if (value < huge(value)) then
      successor=nearest(value,1.0)
      check(n+1)=-dble(successor)
      if (exact_sum(n+1,check(:n+1)) >= 0.d0) then
        value=successor
        successor=nearest(value,1.0)
        check(n+1)=-dble(successor)
        if (exact_sum(n+1,check(:n+1)) >= 0.d0) error stop 'INTERCEPTION ROUNDING'
      end if
    end if
  end function bounded_store
end module interception_expansion

subroutine wb_interception_allocate(rain,melt,irrigation,carry,plant,residue)
  use interception_expansion
  implicit none
  real, intent(in) :: rain,melt,irrigation,carry
  real, intent(inout) :: plant,residue
  double precision :: terms(6)
  terms=(/dble(rain),dble(melt),dble(irrigation),dble(carry),-dble(plant),-dble(residue)/)
  if (exact_sum(5,terms(:5)) <= 0.d0) then
    plant=bounded_store(4,terms(:4))
    residue=0.
  else if (exact_sum(6,terms) <= 0.d0) then
    residue=bounded_store(5,terms(:5))
  end if
end subroutine wb_interception_allocate

! Primitive supplies reach the expansion before aggregation loses low terms.
double precision function wb_interception_input(rain,melt,irrigation,carry,plant,residue)
  use interception_expansion
  implicit none
  real, intent(in) :: rain,melt,irrigation,carry,plant,residue
  wb_interception_input=exact_sum(6,(/dble(rain),dble(melt),dble(irrigation), &
    dble(carry),-dble(plant),-dble(residue)/))
end function wb_interception_input

! Effective-plane p and net-interception coordinates retain their own meanings.
double precision function wb_interception_remaining(supply,carry,plant,residue)
  use interception_expansion
  implicit none
  double precision, intent(in) :: supply
  real, intent(in) :: carry,plant,residue
  wb_interception_remaining=exact_sum(4,(/supply,dble(carry),-dble(plant),-dble(residue)/))
end function wb_interception_remaining
