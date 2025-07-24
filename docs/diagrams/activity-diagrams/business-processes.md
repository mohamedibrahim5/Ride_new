# Business Process Activity Diagrams

## Customer Ride Booking Process

```mermaid
flowchart TD
    Start([Customer opens app]) --> Auth{Authenticated?}
    Auth -->|No| Login[Login/Register Process]
    Login --> Auth
    Auth -->|Yes| Location[Get current location]
    
    Location --> SetPickup[Set pickup location]
    SetPickup --> SetDestination[Set destination]
    SetDestination --> SelectService[Choose service type]
    
    SelectService --> PriceCalc[Calculate price estimate]
    PriceCalc --> ShowPrice[Display price to customer]
    ShowPrice --> Confirm{Confirm booking?}
    
    Confirm -->|No| SelectService
    Confirm -->|Yes| CreateRequest[Create ride request]
    
    CreateRequest --> BroadcastRequest[Broadcast to nearby providers]
    BroadcastRequest --> WaitResponse[Wait for provider response]
    
    WaitResponse --> CheckTimeout{Timeout reached?}
    CheckTimeout -->|Yes| TimeoutAction[Handle timeout]
    TimeoutAction --> Retry{Retry booking?}
    Retry -->|Yes| BroadcastRequest
    Retry -->|No| CancelRequest[Cancel request]
    
    CheckTimeout -->|No| ProviderResponse{Provider responds?}
    ProviderResponse -->|Accept| RideAccepted[Ride accepted]
    ProviderResponse -->|Reject| WaitResponse
    
    RideAccepted --> TrackProvider[Track provider location]
    TrackProvider --> ProviderStatus{Provider status?}
    
    ProviderStatus -->|Starting| TrackProvider
    ProviderStatus -->|Arriving| WaitPickup[Wait at pickup location]
    ProviderStatus -->|Arrived| StartRide[Start ride]
    ProviderStatus -->|Cancelled| HandleCancel[Handle cancellation]
    
    StartRide --> InTransit[Ride in progress]
    InTransit --> TrackRide[Track ride progress]
    TrackRide --> RideComplete{Ride completed?}
    
    RideComplete -->|No| TrackRide
    RideComplete -->|Yes| ProcessPayment[Process payment]
    
    ProcessPayment --> PaymentSuccess{Payment successful?}
    PaymentSuccess -->|No| RetryPayment[Retry payment]
    RetryPayment --> PaymentSuccess
    PaymentSuccess -->|Yes| RateDriver[Rate driver]
    
    RateDriver --> UpdateHistory[Update ride history]
    UpdateHistory --> End([End])
    
    CancelRequest --> End
    HandleCancel --> End
    
    style Start fill:#e1f5fe
    style End fill:#c8e6c9
    style CreateRequest fill:#fff3e0
    style RideAccepted fill:#e8f5e8
    style ProcessPayment fill:#f3e5f5
```

## Provider Ride Acceptance Process

```mermaid
flowchart TD
    Start([Provider goes online]) --> SetAvailable[Set status to available]
    SetAvailable --> ListenRequests[Listen for ride requests]
    
    ListenRequests --> NewRequest{New ride request?}
    NewRequest -->|No| ListenRequests
    NewRequest -->|Yes| DisplayRequest[Display ride details]
    
    DisplayRequest --> CheckDistance[Check distance to pickup]
    CheckDistance --> CheckPrice[Check ride price]
    CheckPrice --> ProviderDecision{Accept ride?}
    
    ProviderDecision -->|No| RejectRide[Reject ride]
    ProviderDecision -->|Yes| AcceptRide[Accept ride]
    
    RejectRide --> ListenRequests
    
    AcceptRide --> LockRide[Attempt to lock ride]
    LockRide --> LockSuccess{Lock successful?}
    
    LockSuccess -->|No| RideAlreadyTaken[Ride already taken]
    RideAlreadyTaken --> ListenRequests
    
    LockSuccess -->|Yes| UpdateStatus[Update status to accepted]
    UpdateStatus --> NotifyCustomer[Notify customer]
    NotifyCustomer --> NavigatePickup[Navigate to pickup location]
    
    NavigatePickup --> UpdateLocation[Update location continuously]
    UpdateLocation --> ArrivedPickup{Arrived at pickup?}
    
    ArrivedPickup -->|No| UpdateLocation
    ArrivedPickup -->|Yes| NotifyArrival[Notify customer of arrival]
    
    NotifyArrival --> WaitCustomer[Wait for customer]
    WaitCustomer --> CustomerReady{Customer ready?}
    
    CustomerReady -->|No| WaitCustomer
    CustomerReady -->|Yes| StartRide[Start ride]
    
    StartRide --> NavigateDestination[Navigate to destination]
    NavigateDestination --> UpdateLocationInRide[Update location during ride]
    UpdateLocationInRide --> ArrivedDestination{Arrived at destination?}
    
    ArrivedDestination -->|No| UpdateLocationInRide
    ArrivedDestination -->|Yes| CompleteRide[Complete ride]
    
    CompleteRide --> ProcessPayment[Process payment]
    ProcessPayment --> RateCustomer[Rate customer]
    RateCustomer --> UpdateEarnings[Update earnings]
    UpdateEarnings --> SetAvailable
    
    style Start fill:#e1f5fe
    style SetAvailable fill:#c8e6c9
    style AcceptRide fill:#fff3e0
    style CompleteRide fill:#e8f5e8
```

## Product Purchase Process

```mermaid
flowchart TD
    Start([Customer browses products]) --> ViewProducts[Display product catalog]
    ViewProducts --> SelectProduct[Select product]
    SelectProduct --> ViewDetails[View product details]
    
    ViewDetails --> CheckStock{Product in stock?}
    CheckStock -->|No| OutOfStock[Show out of stock message]
    OutOfStock --> ViewProducts
    
    CheckStock -->|Yes| AddToCart[Add to cart]
    AddToCart --> ContinueShopping{Continue shopping?}
    
    ContinueShopping -->|Yes| ViewProducts
    ContinueShopping -->|No| ReviewCart[Review cart]
    
    ReviewCart --> CheckQuantity[Verify quantities available]
    CheckQuantity --> QuantityOK{All items available?}
    
    QuantityOK -->|No| UpdateCart[Update cart with available quantities]
    UpdateCart --> ReviewCart
    
    QuantityOK -->|Yes| CalculateTotal[Calculate total price]
    CalculateTotal --> ShowPaymentOptions[Show payment options]
    
    ShowPaymentOptions --> PaymentMethod{Select payment method}
    PaymentMethod -->|Points| CheckPoints{Sufficient points?}
    PaymentMethod -->|Money| ProcessMoneyPayment[Process money payment]
    
    CheckPoints -->|No| InsufficientPoints[Show insufficient points message]
    InsufficientPoints --> ShowPaymentOptions
    
    CheckPoints -->|Yes| DeductPoints[Deduct points from account]
    DeductPoints --> CreateOrder[Create purchase order]
    
    ProcessMoneyPayment --> PaymentSuccess{Payment successful?}
    PaymentSuccess -->|No| PaymentFailed[Show payment failed message]
    PaymentFailed --> ShowPaymentOptions
    PaymentSuccess -->|Yes| CreateOrder
    
    CreateOrder --> UpdateStock[Update product stock]
    UpdateStock --> NotifyProvider[Notify provider of new order]
    NotifyProvider --> SendConfirmation[Send order confirmation to customer]
    
    SendConfirmation --> TrackOrder[Track order status]
    TrackOrder --> OrderStatus{Order status?}
    
    OrderStatus -->|Confirmed| WaitProcessing[Wait for provider processing]
    OrderStatus -->|In Progress| TrackProgress[Track order progress]
    OrderStatus -->|Completed| OrderComplete[Order completed]
    OrderStatus -->|Cancelled| HandleCancellation[Handle order cancellation]
    
    WaitProcessing --> TrackOrder
    TrackProgress --> TrackOrder
    
    OrderComplete --> RateProduct[Rate product and service]
    RateProduct --> UpdateHistory[Update purchase history]
    UpdateHistory --> End([End])
    
    HandleCancellation --> RefundProcess[Process refund]
    RefundProcess --> End
    
    style Start fill:#e1f5fe
    style CreateOrder fill:#fff3e0
    style OrderComplete fill:#c8e6c9
    style End fill:#c8e6c9
```

## Car Rental Booking Process

```mermaid
flowchart TD
    Start([Customer wants to rent car]) --> BrowseCars[Browse available cars]
    BrowseCars --> FilterCars[Apply filters (brand, price, location)]
    FilterCars --> SelectCar[Select car]
    
    SelectCar --> ViewCarDetails[View car details and images]
    ViewCarDetails --> SelectDateTime[Select rental date and time]
    
    SelectDateTime --> CheckAvailability[Check car availability]
    CheckAvailability --> AvailabilityResult{Car available?}
    
    AvailabilityResult -->|No| ShowAlternatives[Show alternative times/cars]
    ShowAlternatives --> SelectDateTime
    
    AvailabilityResult -->|Yes| CalculatePrice[Calculate rental price]
    CalculatePrice --> ShowPricing[Show pricing breakdown]
    
    ShowPricing --> ConfirmBooking{Confirm booking?}
    ConfirmBooking -->|No| SelectDateTime
    
    ConfirmBooking -->|Yes| ValidateBooking[Validate booking details]
    ValidateBooking --> CheckOverlap[Check for time overlaps]
    
    CheckOverlap --> OverlapFound{Overlap detected?}
    OverlapFound -->|Yes| BookingConflict[Show booking conflict]
    BookingConflict --> SelectDateTime
    
    OverlapFound -->|No| CreateRental[Create rental booking]
    CreateRental --> ProcessPayment[Process payment]
    
    ProcessPayment --> PaymentResult{Payment successful?}
    PaymentResult -->|No| PaymentError[Handle payment error]
    PaymentError --> ProcessPayment
    
    PaymentResult -->|Yes| ConfirmRental[Confirm rental booking]
    ConfirmRental --> UpdateAvailability[Update car availability]
    UpdateAvailability --> NotifyProvider[Notify car provider]
    
    NotifyProvider --> SendConfirmation[Send booking confirmation]
    SendConfirmation --> RentalActive[Rental booking active]
    
    RentalActive --> RentalTime{Rental time arrived?}
    RentalTime -->|No| WaitRentalTime[Wait for rental time]
    WaitRentalTime --> RentalTime
    
    RentalTime -->|Yes| StartRental[Start rental period]
    StartRental --> TrackRental[Track rental status]
    
    TrackRental --> RentalEnd{Rental period ended?}
    RentalEnd -->|No| TrackRental
    RentalEnd -->|Yes| CompleteRental[Complete rental]
    
    CompleteRental --> ProcessReturn[Process car return]
    ProcessReturn --> InspectCar[Inspect car condition]
    InspectCar --> CalculateFinalCost[Calculate final cost]
    
    CalculateFinalCost --> ProcessFinalPayment[Process any additional charges]
    ProcessFinalPayment --> RateExperience[Rate rental experience]
    RateExperience --> UpdateHistory[Update rental history]
    UpdateHistory --> End([End])
    
    style Start fill:#e1f5fe
    style CreateRental fill:#fff3e0
    style CompleteRental fill:#e8f5e8
    style End fill:#c8e6c9
```

## Provider Onboarding Process

```mermaid
flowchart TD
    Start([Provider decides to join]) --> RegisterAccount[Register provider account]
    RegisterAccount --> VerifyPhone[Verify phone number with OTP]
    VerifyPhone --> CompleteProfile[Complete basic profile]
    
    CompleteProfile --> SelectServices[Select services to offer]
    SelectServices --> ServiceType{Service type?}
    
    ServiceType -->|Transportation| SetupDriver[Setup driver profile]
    ServiceType -->|Food Delivery| SetupRestaurant[Setup restaurant profile]
    ServiceType -->|Maintenance| SetupMaintenance[Setup maintenance services]
    ServiceType -->|Car Rental| SetupCarAgency[Setup car rental business]
    ServiceType -->|Store| SetupStore[Setup online store]
    
    SetupDriver --> UploadDriverDocs[Upload driver license and documents]
    UploadDriverDocs --> AddVehicle[Add vehicle information]
    AddVehicle --> UploadVehicleDocs[Upload vehicle documents]
    UploadVehicleDocs --> DriverComplete[Driver setup complete]
    
    SetupRestaurant --> RestaurantDetails[Add restaurant details]
    RestaurantDetails --> UploadMenu[Upload menu and prices]
    UploadMenu --> RestaurantComplete[Restaurant setup complete]
    
    SetupMaintenance --> MaintenanceServices[Select maintenance sub-services]
    MaintenanceServices --> SetServiceArea[Set service area]
    SetServiceArea --> MaintenanceComplete[Maintenance setup complete]
    
    SetupCarAgency --> AddCars[Add cars to fleet]
    AddCars --> SetCarPricing[Set car rental pricing]
    SetCarPricing --> SetAvailability[Set car availability]
    SetAvailability --> CarAgencyComplete[Car agency setup complete]
    
    SetupStore --> AddProducts[Add products to store]
    AddProducts --> SetProductPricing[Set product pricing]
    SetProductPricing --> StoreComplete[Store setup complete]
    
    DriverComplete --> SetPricing[Set service pricing]
    RestaurantComplete --> SetPricing
    MaintenanceComplete --> SetPricing
    CarAgencyComplete --> SetPricing
    StoreComplete --> SetPricing
    
    SetPricing --> SubmitForReview[Submit for admin review]
    SubmitForReview --> WaitReview[Wait for admin verification]
    
    WaitReview --> ReviewResult{Review result?}
    ReviewResult -->|Approved| AccountApproved[Account approved]
    ReviewResult -->|Rejected| ReviewFeedback[Receive feedback]
    ReviewResult -->|Needs Changes| RequestChanges[Request changes]
    
    ReviewFeedback --> End([Registration rejected])
    RequestChanges --> MakeChanges[Make requested changes]
    MakeChanges --> SubmitForReview
    
    AccountApproved --> GoLive[Go live and start accepting requests]
    GoLive --> ProviderActive[Provider account active]
    ProviderActive --> Success([Onboarding complete])
    
    style Start fill:#e1f5fe
    style AccountApproved fill:#c8e6c9
    style Success fill:#c8e6c9
    style End fill:#ffcdd2
```

## Key Process Features

### Parallel Processing
- Location updates happen concurrently with ride progress
- Multiple providers can receive requests simultaneously
- Background tasks process payments and notifications

### Error Handling
- Timeout mechanisms for unresponsive providers
- Retry logic for failed payments
- Fallback options for unavailable services

### Business Rules Enforcement
- Stock validation before purchase completion
- Availability checks before booking confirmation
- Verification requirements for provider onboarding

### User Experience Optimization
- Real-time status updates
- Immediate feedback on user actions
- Clear error messages and recovery options

### Scalability Considerations
- Asynchronous processing for heavy operations
- Caching for frequently accessed data
- Load balancing for high-traffic scenarios