package readers;

import java.util.List;

import model.input.GetPosition;
import model.input.GetPosition.Position;
import model.input.getposition.Current;
import model.input.getposition.Down;
import model.input.getposition.Left;
import model.input.getposition.Previous;
import model.input.getposition.Primary;
import model.input.getposition.Right;
import model.input.getposition.Secondary;
import model.input.getposition.Up;
import model.input.getposition.XYValue;

public class PositionReaderImpl implements PositionReader {

	@Override
	public GetPosition readPosition(List<String> values) {
		Position position = Position.valueOf(values.get(0));
		switch (position) {
		case XY_VALUE:
			values.remove(0);
			int x = Integer.valueOf(values.get(0));
			values.remove(0);
			int y = Integer.valueOf(values.get(0));
			values.remove(0);
			return new XYValue(x, y);
		case PRIMARY:
			values.remove(0);
			return new Primary();
		case SECONDARY:
			values.remove(0);
			return new Secondary();
		case LEFT:
			values.remove(0);
			return new Left();
		case RIGHT:
			values.remove(0);
			return new Right();
		case UP:
			values.remove(0);
			return new Up();
		case DOWN:
			values.remove(0);
			return new Down();
		case CURRENT:
			values.remove(0);
			return new Current();
		case PREVIOUS:
			values.remove(0);
			return new Previous();
		default:
			return null;
		}
	}
}
