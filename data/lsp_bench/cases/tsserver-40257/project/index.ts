export type CCResponsePredicate<
	TSent extends CommandClass = CommandClass,
	TReceived extends CommandClass = CommandClass
> = (sentCommand: CommandClass, receivedCommand: CommandClass) => CCResponseRole;
