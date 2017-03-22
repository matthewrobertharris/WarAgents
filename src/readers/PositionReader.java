package readers;

import java.util.List;

import model.input.GetPosition;

public interface PositionReader {

	public GetPosition readPosition(List<String> values);
}
