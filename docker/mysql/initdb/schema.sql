-- Create syntax for TABLE 'bitmexPrice'

CREATE TABLE `TradeStatus` (
  `id` float NOT NULL PRIMARY KEY,
  `TurnON` float DEFAULT 1,
  `KeepPosition` float DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
